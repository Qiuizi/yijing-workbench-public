/**
 * 交互回归：主题切换、图鉴选择/搜索、图库切换、复制、起卦链路、外观设置。
 * 无第三方依赖，直接走 Chrome DevTools Protocol（Node 22 自带 WebSocket）。
 *
 * 用法： node scripts/ui-regression.mjs
 * 前置：官网 dev 在 5191，桌面端 dev 在 5194（可改下方 URL）。
 */
import { spawn } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PORT = 9334
const SITE = 'http://localhost:5191/yijing-workbench-public/'
const APP = 'http://127.0.0.1:5194/'
const profile = `${process.env.TEMP ?? '.'}\\yijing-regression-profile`

const chrome = spawn(
  CHROME,
  [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    `--user-data-dir=${profile}`,
    `--remote-debugging-port=${PORT}`,
    'about:blank',
  ],
  { stdio: 'ignore' },
)

let devtoolsBase = null

// Chrome 在不同环境下可能只绑 IPv6 或 IPv4，这里两边都试。
async function waitForDevtools() {
  for (let i = 0; i < 120; i += 1) {
    for (const host of ['[::1]', '127.0.0.1']) {
      try {
        const res = await fetch(`http://${host}:${PORT}/json/version`)
        if (res.ok) {
          devtoolsBase = `http://${host}:${PORT}`
          return
        }
      } catch {
        /* not up yet */
      }
    }
    await sleep(150)
  }
  throw new Error('devtools did not start')
}

class Cdp {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    this.listeners = new Map()
    this.errors = []
    ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else resolve(msg.result)
      } else if (msg.method) {
        if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
          this.errors.push(msg.params.args.map((a) => a.value ?? a.description ?? '').join(' '))
        }
        if (msg.method === 'Runtime.exceptionThrown') {
          this.errors.push(msg.params.exceptionDetails?.text ?? 'exception')
        }
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

  async evaluate(expression, userGesture = false) {
    const res = await this.send('Runtime.evaluate', {
      expression: `(() => { ${expression} })()`,
      returnByValue: true,
      awaitPromise: true,
      userGesture,
    })
    if (res.exceptionDetails) throw new Error(res.exceptionDetails.text)
    return res.result.value
  }
}

const results = []
function check(name, ok, detail = '') {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`)
}

async function goto(cdp, url, wait = 900) {
  const loaded = cdp.once('Page.loadEventFired')
  await cdp.send('Page.navigate', { url })
  await Promise.race([loaded.catch(() => {}), sleep(8000)])
  await sleep(wait)
}

async function main() {
  await waitForDevtools()
  const target = await (await fetch(`${devtoolsBase}/json/new?about:blank`, { method: 'PUT' })).json()
  const ws = new WebSocket(target.webSocketDebuggerUrl)
  await new Promise((ok, bad) => {
    ws.addEventListener('open', ok, { once: true })
    ws.addEventListener('error', bad, { once: true })
  })
  const cdp = new Cdp(ws)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Page.bringToFront')
  await cdp.send('Browser.grantPermissions', {
    // 权限按 origin 授权，不能带路径
    origin: new URL(SITE).origin,
    permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'],
  })
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  })

  // ---------------- 官网 ----------------
  await goto(cdp, SITE, 1400)
  await cdp.evaluate(`localStorage.removeItem('yijing-theme'); return true;`)
  await goto(cdp, SITE, 1200)

  const initialTheme = await cdp.evaluate(`return document.documentElement.dataset.theme`)
  check('site: 默认主题可解析', initialTheme === 'light' || initialTheme === 'dark', initialTheme)

  await cdp.evaluate(`document.querySelector('.theme-toggle').click(); return true;`)
  await sleep(320)
  const afterToggle = await cdp.evaluate(`
    return {
      theme: document.documentElement.dataset.theme,
      stored: localStorage.getItem('yijing-theme'),
      scheme: getComputedStyle(document.documentElement).colorScheme,
    }
  `)
  check(
    'site: 主题按钮切换并持久化',
    afterToggle.theme === 'dark' && afterToggle.stored === 'dark' && afterToggle.scheme === 'dark',
    JSON.stringify(afterToggle),
  )
  await cdp.evaluate(`document.querySelector('.theme-toggle').click(); return true;`)
  await sleep(200)

  const atlasCells = await cdp.evaluate(`
    const cells = [...document.querySelectorAll('.atlas__grid .cell')];
    cells[63]?.click();
    return { before: cells.length };
  `)
  await sleep(320)
  const atlas = await cdp.evaluate(`
    const detail = document.querySelector('.detail__num')?.textContent.trim();
    const input = document.querySelector('.atlas__search input');
    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    set.call(input, '乾');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return { before: ${atlasCells.before}, detail };
  `)
  await sleep(320)
  const atlasAfterSearch = await cdp.evaluate(`
    return {
      after: document.querySelectorAll('.atlas__grid .cell').length,
      selected: document.querySelector('.cell.is-selected')?.dataset.order ?? null,
    }
  `)
  check('site: 图鉴 64 格可选中', atlas.before === 64 && atlas.detail === '64', JSON.stringify(atlas))
  check('site: 图鉴搜索收敛结果', atlasAfterSearch.after > 0 && atlasAfterSearch.after < 64, JSON.stringify(atlasAfterSearch))

  const galleryCount = await cdp.evaluate(`
    document.querySelector('[data-index="3"]')?.click();
    return { count: document.querySelectorAll('.gallery__thumb').length };
  `)
  await sleep(320)
  const gallery = await cdp.evaluate(`
    const idx = document.querySelector('.gallery__main-cap-index')?.textContent.replace(/\\s+/g, '');
    document.querySelector('[data-index="3"]')?.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    return { idx, count: ${galleryCount.count} };
  `)
  await sleep(320)
  const galleryAfter = await cdp.evaluate(`
    return document.querySelector('.gallery__main-cap-index')?.textContent.replace(/\\s+/g, '')
  `)
  check('site: 图库 9 张可切换', gallery.count === 9 && gallery.idx?.includes('04'), JSON.stringify(gallery))
  check('site: 图库方向键切换', galleryAfter?.includes('05'), String(galleryAfter))

  await cdp.evaluate(`document.querySelector('.dl-copy')?.click(); return true;`, true)
  await sleep(260)
  const copyState = await cdp.evaluate(`
    const btn = document.querySelector('.dl-copy');
    return { copied: btn?.classList.contains('is-copied'), text: btn?.textContent.trim() };
  `)
  check('site: SHA 复制反馈', copyState.copied === true, JSON.stringify(copyState))

  await goto(cdp, SITE + 'en/', 1200)
  const en = await cdp.evaluate(`
    return {
      lang: document.documentElement.lang,
      title: document.querySelector('h1')?.textContent.trim(),
      nav: document.querySelectorAll('.nav-desktop a').length,
      theme: !!document.querySelector('.theme-toggle'),
    }
  `)
  check('site: 英文页完整', en.lang === 'en' && en.nav === 4 && en.theme, JSON.stringify(en))

  // ---------------- 桌面端 ----------------
  await goto(cdp, APP, 1200)
  await cdp.evaluate(`localStorage.removeItem('yijing-appearance'); return true;`)
  await goto(cdp, APP, 1200)

  await cdp.evaluate(`document.querySelector('.appearance-toggle').click(); return true;`)
  await sleep(300)
  const appTheme = await cdp.evaluate(`
    return {
      theme: document.documentElement.dataset.theme,
      darkClass: document.documentElement.classList.contains('dark'),
      stored: localStorage.getItem('yijing-appearance'),
      bg: getComputedStyle(document.body).backgroundColor,
    }
  `)
  check(
    'app: 顶栏主题按钮切换',
    appTheme.theme === 'dark' && appTheme.darkClass && appTheme.stored === 'dark',
    JSON.stringify(appTheme),
  )

  const cast = await cdp.evaluate(`
    const el = document.querySelector('#question');
    const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    set.call(el, '回归测试：是否应该继续打磨这一版界面？');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    document.querySelector('.cast-button').click();
    return true;
  `)
  void cast
  await sleep(1400)
  const result = await cdp.evaluate(`
    return {
      heading: document.querySelector('.result-heading h1')?.textContent.trim(),
      tabs: document.querySelectorAll('.result-tabs button').length,
      cards: document.querySelectorAll('.hexagram-card').length,
      date: document.querySelector('.result-toolbar span')?.textContent.trim(),
    }
  `)
  check(
    'app: 起卦链路（问句 / 四标签 / 双卦卡）',
    result.tabs === 4 && result.cards === 2 && result.heading?.includes('回归测试'),
    JSON.stringify(result),
  )

  await cdp.evaluate(`
    const tabs = [...document.querySelectorAll('.result-tabs button')];
    tabs[2].click();
    return true;
  `)
  await sleep(900)
  const najiaPanel = await cdp.evaluate(`
    return {
      controls: document.querySelectorAll('.najia-controls').length,
      generate: [...document.querySelectorAll('.najia-controls .el-button')].some((b) => b.textContent.includes('生成')),
      active: document.querySelector('.result-tabs button[aria-current]')?.textContent.trim(),
    }
  `)
  check('app: 六爻排盘页可打开', najiaPanel.controls === 1 && najiaPanel.generate, JSON.stringify(najiaPanel))

  await cdp.evaluate(`
    const btn = [...document.querySelectorAll('.najia-controls .el-button')].find((b) => b.textContent.includes('生成'));
    btn?.click();
    return true;
  `, true)
  await sleep(1600)
  const najiaRows = await cdp.evaluate(`
    return {
      rows: document.querySelectorAll('.najia-table tbody tr').length,
      lastCell: document.querySelector('.najia-table tbody tr:last-child td')?.textContent.trim(),
    }
  `)
  check('app: 排盘表 6 爻生成', najiaRows.rows === 6, JSON.stringify(najiaRows))

  await goto(cdp, APP + '#/settings', 1400)
  const settings = await cdp.evaluate(`
    const groups = [...document.querySelectorAll('.settings-group h3')].map((h) => h.textContent.trim());
    return { groups, hasAppearance: groups.includes('外观') };
  `)
  check('app: 设置页含外观分组', settings.hasAppearance === true, JSON.stringify(settings.groups))

  await cdp.evaluate(`
    const labels = [...document.querySelectorAll('.el-radio-button')];
    const light = labels.find((l) => l.textContent.trim() === '浅色');
    light?.click();
    return true;
  `)
  await sleep(300)
  const afterLight = await cdp.evaluate(`
    return {
      theme: document.documentElement.dataset.theme,
      stored: localStorage.getItem('yijing-appearance'),
    }
  `)
  check(
    'app: 设置页切回浅色并持久化',
    afterLight.theme === 'light' && afterLight.stored === 'light',
    JSON.stringify(afterLight),
  )

  const consoleErrors = cdp.errors.filter((e) => !e.includes('favicon'))
  check('两端控制台无错误', consoleErrors.length === 0, consoleErrors.slice(0, 3).join(' | '))

  const failed = results.filter((r) => !r.ok)
  console.log(`\n${results.length - failed.length}/${results.length} 通过`)
  chrome.kill()
  process.exit(failed.length === 0 ? 0 : 1)
}

main().catch((error) => {
  console.error(error)
  chrome.kill()
  process.exit(1)
})
