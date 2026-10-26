/**
 * 夜间字号可读性核对：同一元素在浅色 / 夜间下的计算字号，逐个比对。
 *
 * 规则（与验收标准一致）：
 *   1. 浅色下 ≤ 12px 的微小文字，夜间不得再缩小；
 *   2. 夜间任何阅读文字不得小于 12px（输入、提示、状态优先可读）；
 *   3. 同一元素两套主题的字号差不得超过 2px（避免布局跳动）。
 *
 * 用法： node scripts/type-readability.mjs [--json out.json]
 * 退出码：0 全部符合；1 存在不符合项；2 执行失败。
 */
import { spawn } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PORT = Number(process.env.TYPE_PORT ?? 9339)
const PROFILE = `${process.env.TEMP ?? '.'}\\yijing-type-profile`

const PAGES = [
  { name: 'app:home', url: 'http://127.0.0.1:5194/', key: 'yijing-appearance' },
  { name: 'app:history', url: 'http://127.0.0.1:5194/#/history', key: 'yijing-appearance' },
  { name: 'app:settings', url: 'http://127.0.0.1:5194/#/settings', key: 'yijing-appearance' },
  { name: 'app:learning', url: 'http://127.0.0.1:5194/#/learning', key: 'yijing-appearance' },
  { name: 'site:home', url: 'http://localhost:5191/yijing-workbench-public/', key: 'yijing-theme' },
]

const COLLECT_JS = `
  const pathOf = (el) => {
    const bits = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const tag = n.tagName.toLowerCase();
      const idx = n.parentElement ? [...n.parentElement.children].indexOf(n) : 0;
      bits.unshift(tag + ':' + idx);
    }
    return bits.join('/');
  };
  const out = {};
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const text = node.textContent.trim();
    if (!text) continue;
    const el = node.parentElement;
    if (!el) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;
    const key = pathOf(el);
    if (out[key]) continue;
    out[key] = {
      size: Math.round(parseFloat(cs.fontSize) * 100) / 100,
      cls: (el.className && String(el.className).split(' ').slice(0, 2).join('.')) || '',
      tag: el.tagName.toLowerCase(),
      text: text.slice(0, 30),
    };
  }
  return out;
`

class Cdp {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    this.listeners = new Map()
    ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else resolve(msg.result)
      } else if (msg.method) {
        for (const fn of this.listeners.get(msg.method) ?? []) fn(msg.params)
      }
    })
  }
  send(method, params = {}) {
    const id = (this.id += 1)
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }
  once(method) {
    return new Promise((resolve) => {
      const list = this.listeners.get(method) ?? []
      const fn = (params) => {
        this.listeners.set(method, (this.listeners.get(method) ?? []).filter((f) => f !== fn))
        resolve(params)
      }
      this.listeners.set(method, [...list, fn])
    })
  }
  async evaluate(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression: `(async () => { ${expression} })()`,
      returnByValue: true,
      awaitPromise: true,
    })
    if (res.exceptionDetails) throw new Error(res.exceptionDetails.exception?.description ?? res.exceptionDetails.text)
    return res.result.value
  }
}

async function goto(cdp, url, wait = 1300) {
  const blank = cdp.once('Page.loadEventFired')
  await cdp.send('Page.navigate', { url: 'about:blank' })
  await Promise.race([blank, sleep(2000)])
  const loaded = cdp.once('Page.loadEventFired')
  const nav = await cdp.send('Page.navigate', { url })
  if (nav.errorText) throw new Error(`导航失败: ${nav.errorText}`)
  await Promise.race([loaded, sleep(15000)])
  await sleep(wait)
}

async function collect(cdp, page, theme) {
  await goto(cdp, page.url)
  await cdp.evaluate(`localStorage.setItem(${JSON.stringify(page.key)}, ${JSON.stringify(theme)}); return true`)
  const loaded = cdp.once('Page.loadEventFired')
  await cdp.send('Page.reload', { ignoreCache: true })
  await Promise.race([loaded, sleep(15000)])
  await sleep(1400)
  const actual = await cdp.evaluate(`return document.documentElement.dataset.theme || null`)
  if (page.key === 'yijing-appearance' && actual !== theme) throw new Error(`${page.name}: 主题未生效（${actual}）`)
  const nodes = await cdp.evaluate(`return (() => { ${COLLECT_JS} })()`)
  if (!nodes || Object.keys(nodes).length === 0) throw new Error(`${page.name}: 没有采集到文字节点`)
  return nodes
}

async function main() {
  const args = process.argv.slice(2)
  const jsonIndex = args.indexOf('--json')
  const jsonPath = jsonIndex >= 0 ? args[jsonIndex + 1] : null

  const chrome = spawn(
    CHROME,
    [
      '--headless=new',
      '--disable-gpu',
      '--hide-scrollbars',
      '--no-first-run',
      `--user-data-dir=${PROFILE}`,
      `--remote-debugging-port=${PORT}`,
      'about:blank',
    ],
    { stdio: 'ignore' },
  )
  let cdp = null
  try {
    let base = null
    for (let i = 0; i < 120 && !base; i += 1) {
      for (const host of ['[::1]', '127.0.0.1']) {
        try {
          const res = await fetch(`http://${host}:${PORT}/json/version`)
          if (res.ok) {
            base = `http://${host}:${PORT}`
            break
          }
        } catch {
          /* retry */
        }
      }
      if (!base) await sleep(150)
    }
    if (!base) throw new Error('Chrome DevTools 未启动')

    const target = await (await fetch(`${base}/json/new?about:blank`, { method: 'PUT' })).json()
    const ws = new WebSocket(target.webSocketDebuggerUrl)
    await new Promise((ok, bad) => {
      ws.addEventListener('open', ok, { once: true })
      ws.addEventListener('error', () => bad(new Error('WebSocket 连接失败')), { once: true })
    })
    cdp = new Cdp(ws)
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })

    const report = { pages: [], problems: [] }
    for (const page of PAGES) {
      const light = await collect(cdp, page, 'light')
      const dark = await collect(cdp, page, 'dark')
      const rows = []
      for (const key of Object.keys(light)) {
        const l = light[key]
        const d = dark[key]
        if (!d) continue
        const delta = Math.round((d.size - l.size) * 100) / 100
        const problems = []
        if (l.size <= 12 && delta < 0) problems.push(`浅色 ${l.size}px 的微字在夜间缩小了 ${Math.abs(delta)}px`)
        if (d.size < 12 && l.size >= 12) problems.push(`夜间 ${d.size}px 低于 12px 下限（浅色 ${l.size}px）`)
        if (Math.abs(delta) > 2) problems.push(`字差 ${delta}px 超过 2px`)
        rows.push({ key, cls: l.cls, text: l.text, light: l.size, dark: d.size, delta, problems })
        if (problems.length) report.problems.push({ page: page.name, ...rows[rows.length - 1] })
      }
      const shrunk = rows.filter((r) => r.delta < 0)
      const minDark = rows.reduce((acc, r) => Math.min(acc, r.dark), 99)
      report.pages.push({
        name: page.name,
        nodes: rows.length,
        shrunk: shrunk.length,
        minLight: rows.reduce((a, r) => Math.min(a, r.light), 99),
        minDark,
      })
      console.log(
        `\n=== ${page.name} === 节点 ${rows.length} · 收窄 ${shrunk.length} · 最小字号 浅色 ${report.pages.at(-1).minLight} / 夜间 ${minDark}`,
      )
      const shown = rows.filter((r) => r.delta !== 0).sort((a, b) => a.delta - b.delta).slice(0, 8)
      for (const r of shown) {
        console.log(`  ${r.light}→${r.dark}px (${r.delta > 0 ? '+' : ''}${r.delta})  ${r.cls || r.text}`)
      }
    }

    if (jsonPath) writeFileSync(jsonPath, `${JSON.stringify(report, null, 2)}\n`, 'utf-8')

    if (report.problems.length) {
      console.log(`\n不合规 ${report.problems.length} 处：`)
      for (const p of report.problems.slice(0, 20)) {
        console.log(`  [${p.page}] ${p.light}→${p.dark}px ${p.cls || p.text} — ${p.problems.join('；')}`)
      }
      return 1
    }
    console.log('\n全部符合：微小文字未再缩小，夜间无 <12px 阅读文字，字差 ≤ 2px')
    return 0
  } catch (error) {
    console.error(`\n执行失败：${error.message}`)
    return 2
  } finally {
    try {
      cdp?.ws.close()
    } catch {
      /* ignore */
    }
    try {
      chrome.kill()
    } catch {
      /* ignore */
    }
  }
}

main().then((code) => process.exit(code))
