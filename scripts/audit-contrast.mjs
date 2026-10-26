/**
 * DOM 级对比度审计：逐个文字节点算「有效背景」与 WCAG 比值。
 * 比 token 校验更狠——它能抓到遗留的写死色值。
 *
 * 用法：
 *   node scripts/audit-contrast.mjs                 # 审计内置的 10 个页面/主题组合
 *   node scripts/audit-contrast.mjs --min 4.5       # 统一阈值（覆盖 AA 的分级规则）
 *   node scripts/audit-contrast.mjs --url name=http://host/page@dark
 *   node scripts/audit-contrast.mjs --json out.json --quiet
 *
 * 阈值：
 *   默认按 WCAG AA —— 正文 4.5:1；大字（>=24px，或 >=18.66px 且 600 字重）3.0:1。
 *   --min <ratio> 指定后，所有文字统一使用该阈值（用于严格验收，例如 4.5）。
 *
 * 退出码：
 *   0  通过：全部页面完成审计，0 违规，0 未评估
 *   1  违规：存在低于阈值的文字节点
 *   2  执行失败：Chrome/CDP/页面加载/脚本异常，或页面没有完成扫描
 *   3  未评估：无违规，但存在无法准确计算背景的文字节点（不算通过）
 */
import { spawn } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { setTimeout as sleep } from 'node:timers/promises'

const EXIT = { PASS: 0, VIOLATION: 1, EXECUTION: 2, UNAUDITED: 3 }

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PORT = Number(process.env.AUDIT_PORT ?? 9337)
const PROFILE = `${process.env.TEMP ?? '.'}\\yijing-audit-profile`

const DEFAULT_PAGES = [
  { name: 'site:home:light', url: 'http://localhost:5191/yijing-workbench-public/', theme: 'light', key: 'yijing-theme' },
  { name: 'site:home:dark', url: 'http://localhost:5191/yijing-workbench-public/', theme: 'dark', key: 'yijing-theme' },
  { name: 'app:home:light', url: 'http://127.0.0.1:5194/', theme: 'light', key: 'yijing-appearance' },
  { name: 'app:home:dark', url: 'http://127.0.0.1:5194/', theme: 'dark', key: 'yijing-appearance' },
  { name: 'app:history:dark', url: 'http://127.0.0.1:5194/#/history', theme: 'dark', key: 'yijing-appearance' },
  { name: 'app:history:light', url: 'http://127.0.0.1:5194/#/history', theme: 'light', key: 'yijing-appearance' },
  { name: 'app:settings:dark', url: 'http://127.0.0.1:5194/#/settings', theme: 'dark', key: 'yijing-appearance' },
  { name: 'app:settings:light', url: 'http://127.0.0.1:5194/#/settings', theme: 'light', key: 'yijing-appearance' },
  { name: 'app:learning:dark', url: 'http://127.0.0.1:5194/#/learning', theme: 'dark', key: 'yijing-appearance' },
  { name: 'app:learning:light', url: 'http://127.0.0.1:5194/#/learning', theme: 'light', key: 'yijing-appearance' },
]

// ---------------- args ----------------
function parseArgs(argv) {
  const opts = { min: null, pages: [], json: null, quiet: false, timeout: 20000, urls: false }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--min') opts.min = Number(argv[++i])
    else if (arg === '--json') opts.json = argv[++i]
    else if (arg === '--timeout') opts.timeout = Number(argv[++i])
    else if (arg === '--quiet') opts.quiet = true
    else if (arg === '--url') {
      const raw = argv[++i] ?? ''
      const [head, theme] = raw.split('@')
      const eq = head.indexOf('=')
      const name = eq > 0 ? head.slice(0, eq) : head
      const url = eq > 0 ? head.slice(eq + 1) : head
      opts.pages.push({
        name,
        url,
        theme: theme === 'dark' ? 'dark' : theme === 'light' ? 'light' : null,
        key: url.includes('5191') ? 'yijing-theme' : 'yijing-appearance',
      })
      opts.urls = true
    } else if (arg === '--help' || arg === '-h') {
      console.log('用法: node scripts/audit-contrast.mjs [--min <ratio>] [--url name=url[@light|@dark]] [--json path] [--timeout ms] [--quiet]')
      process.exit(EXIT.PASS)
    } else {
      throw new Error(`unknown argument: ${arg}`)
    }
  }
  if (opts.min !== null) {
    if (!Number.isFinite(opts.min) || opts.min < 1 || opts.min > 21) {
      throw new Error('--min 需要 1..21 之间的数值')
    }
  }
  if (opts.urls) {
    if (opts.pages.length === 0) throw new Error('--url 至少给一个')
  } else {
    opts.pages = DEFAULT_PAGES
  }
  return opts
}

// ---------------- cdp ----------------
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
      expression,
      returnByValue: true,
      awaitPromise: true,
    })
    if (res.exceptionDetails) {
      const detail = res.exceptionDetails.exception?.description ?? res.exceptionDetails.text
      throw new Error(`Runtime.evaluate failed: ${detail}`)
    }
    return res.result.value
  }

  close() {
    try {
      this.ws.close()
    } catch {
      /* already closed */
    }
  }
}

async function launchChrome() {
  const chrome = spawn(
    CHROME,
    [
      '--headless=new',
      '--disable-gpu',
      '--hide-scrollbars',
      '--no-first-run',
      '--no-default-browser-check',
      `--user-data-dir=${PROFILE}`,
      `--remote-debugging-port=${PORT}`,
      'about:blank',
    ],
    { stdio: 'ignore' },
  )
  const exited = new Promise((_, reject) => {
    chrome.on('error', (error) => reject(new Error(`Chrome 启动失败: ${error.message}`)))
    chrome.on('exit', (code) => reject(new Error(`Chrome 提前退出 (code ${code})`)))
  })
  exited.catch(() => {})
  return { chrome, exited }
}

async function devtoolsBase(chrome, exited, timeoutMs) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    for (const host of ['[::1]', '127.0.0.1']) {
      try {
        const res = await fetch(`http://${host}:${PORT}/json/version`)
        if (res.ok) return `http://${host}:${PORT}`
      } catch {
        /* not up yet */
      }
    }
    if (chrome.exitCode !== null) {
      throw new Error(`Chrome 已退出 (code ${chrome.exitCode})`)
    }
    await Promise.race([sleep(150), exited])
  }
  throw new Error(`${timeoutMs}ms 内未等到 DevTools 端口 ${PORT}`)
}

async function connect(base) {
  const res = await fetch(`${base}/json/new?about:blank`, { method: 'PUT' })
  if (!res.ok) throw new Error(`创建 DevTools target 失败: HTTP ${res.status}`)
  const target = await res.json()
  const ws = new WebSocket(target.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('WebSocket 连接超时')), 10000)
    ws.addEventListener(
      'open',
      () => {
        clearTimeout(timer)
        resolve()
      },
      { once: true },
    )
    ws.addEventListener(
      'error',
      () => {
        clearTimeout(timer)
        reject(new Error('WebSocket 连接失败'))
      },
      { once: true },
    )
  })
  return new Cdp(ws)
}

// ---------------- in-page audit ----------------
const AUDIT_JS = String.raw`
(() => {
  const parse = (value) => {
    const m = value.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const parts = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };
  const lum = ({ r, g, b }) => {
    const f = (v) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const blend = (top, bottom) => ({
    r: top.r * top.a + bottom.r * (1 - top.a),
    g: top.g * top.a + bottom.g * (1 - top.a),
    b: top.b * top.a + bottom.b * (1 - top.a),
    a: 1,
  });
  const ratio = (a, b) => {
    const la = lum(a), lb = lum(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  };
  const describe = (c) => 'rgb(' + [c.r, c.g, c.b].map((v) => Math.round(v)).join(',') + ')';
  const cssPath = (el) => {
    const bits = [];
    for (let n = el; n && bits.length < 4; n = n.parentElement) {
      let s = n.tagName.toLowerCase();
      if (n.classList && n.classList.length) s += '.' + [...n.classList].slice(0, 2).join('.');
      bits.unshift(s);
    }
    return bits.join('>');
  };

  // 返回 { bg, reason }：bg 为可用的有效背景；reason 非空表示无法准确计算
  const effectiveBg = (el) => {
    let acc = null;
    for (let node = el; node; node = node.parentElement) {
      const cs = getComputedStyle(node);
      const image = cs.backgroundImage;
      const color = parse(cs.backgroundColor);
      if (image && image !== 'none') {
        // 渐变/图片无法从计算样式还原，且它在文字之下 → 不可评估
        if (!acc || acc.a < 1) {
          return { bg: acc, reason: image.includes('gradient') ? 'gradient-ancestor' : 'image-ancestor' };
        }
      }
      if (!color || color.a === 0) continue;
      acc = acc ? blend(acc, color) : color;
      if (acc.a >= 0.999) return { bg: acc, reason: null };
    }
    if (acc && acc.a > 0) {
      // 没有找到不透明背景：用白色画布兜底，但标注出来
      return { bg: blend(acc, { r: 255, g: 255, b: 255, a: 1 }), reason: 'no-opaque-bg' };
    }
    return { bg: { r: 255, g: 255, b: 255, a: 1 }, reason: 'no-opaque-bg' };
  };

  const violations = [];
  const unaudited = [];
  let scanned = 0;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  let node;
  while ((node = walker.nextNode())) {
    const text = node.textContent.trim();
    if (!text) continue;
    const el = node.parentElement;
    if (!el || seen.has(el)) continue;
    seen.add(el);

    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (el.closest('.sr-only, [hidden], script, style, noscript')) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;           // 被裁掉/未渲染
    const opacity = Number(cs.opacity);
    if (opacity < 0.25) continue;                               // 近乎透明，另行人工判断

    const fgRaw = parse(cs.color);
    if (!fgRaw) continue;
    scanned += 1;

    const { bg, reason } = effectiveBg(el);
    if (reason) {
      unaudited.push({ sel: cssPath(el), text: text.slice(0, 42), reason });
      continue;
    }
    const fg = fgRaw.a < 1 ? blend(fgRaw, bg) : fgRaw;
    // 多层 opacity 叠加（元素本身 + 祖先）按有效 alpha 近似
    const effAlpha = opacity < 1 ? opacity : 1;
    const fgEff = effAlpha < 1 ? blend({ ...fg, a: effAlpha }, bg) : fg;

    const r = ratio(fgEff, bg);
    const size = parseFloat(cs.fontSize);
    const weight = Number(cs.fontWeight) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 600);
    violations.push({
      sel: cssPath(el),
      text: text.slice(0, 42),
      fg: describe(fgEff),
      bg: describe(bg),
      ratio: Math.round(r * 100) / 100,
      size,
      large,
      opacity,
    });
  }
  return { scanned, violations, unaudited };
})()
`

// ---------------- audit one page ----------------
async function auditPage(cdp, page, opts) {
  // 先回 about:blank：hash 路由的同文档跳转不会触发 load 事件
  const blank = cdp.once('Page.loadEventFired')
  await cdp.send('Page.navigate', { url: 'about:blank' })
  await Promise.race([blank, sleep(3000)])

  const loadState = { loaded: false }
  const loaded = cdp.once('Page.loadEventFired').then(() => {
    loadState.loaded = true
  })
  const nav = await cdp.send('Page.navigate', { url: page.url })
  if (nav.errorText) throw new Error(`导航失败: ${nav.errorText}`)
  await Promise.race([loaded, sleep(opts.timeout)])
  if (!loadState.loaded) throw new Error(`${opts.timeout}ms 内未收到 load 事件（页面可能不可达）`)
  await sleep(1200)

  if (page.theme) {
    await cdp.evaluate(
      `localStorage.setItem(${JSON.stringify(page.key)}, ${JSON.stringify(page.theme)}); true`,
    )
    const reloaded = cdp.once('Page.loadEventFired')
    await cdp.send('Page.reload', { ignoreCache: true })
    await Promise.race([reloaded, sleep(opts.timeout)])
    await sleep(1400)
  }

  const ready = await cdp.evaluate(`(() => ({
    state: document.readyState,
    bodyChildren: document.body ? document.body.childElementCount : 0,
    title: document.title,
    theme: document.documentElement.dataset.theme || null,
    url: location.href,
  }))()`)
  if (ready.state !== 'complete') throw new Error(`页面未完成加载（readyState=${ready.state}）`)
  if (ready.bodyChildren === 0) throw new Error('页面 body 为空（前端可能挂载失败）')
  if (page.theme && ready.theme && ready.theme !== page.theme) {
    throw new Error(`主题未生效：期望 ${page.theme}，实际 ${ready.theme}`)
  }

  const result = await cdp.evaluate(AUDIT_JS)
  if (!result || typeof result.scanned !== 'number') throw new Error('审计脚本返回结构异常')
  if (result.scanned === 0) throw new Error('页面没有任何可审计文字节点（疑似白屏）')
  return { ...result, meta: ready }
}

// ---------------- main ----------------
async function main() {
  const opts = parseArgs(process.argv.slice(2))
  const threshold = (node) => {
    if (opts.min !== null) return opts.min
    return node.large ? 3 : 4.5
  }

  let chrome = null
  let cdp = null
  const report = { pages: [], opts: { min: opts.min, timeout: opts.timeout }, generatedAt: new Date().toISOString() }

  try {
    const launched = await launchChrome()
    chrome = launched.chrome
    const base = await devtoolsBase(chrome, launched.exited, opts.timeout)
    cdp = await connect(base)
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 1000,
      deviceScaleFactor: 1,
      mobile: false,
    })

    let totalViolations = 0
    let totalUnaudited = 0

    for (const page of opts.pages) {
      let entry
      try {
        const result = await auditPage(cdp, page, opts)
        const bad = result.violations
          .map((v) => ({ ...v, need: threshold(v) }))
          .filter((v) => v.ratio < v.need)
          .sort((a, b) => a.ratio - b.ratio)
        entry = {
          name: page.name,
          url: page.url,
          theme: page.theme,
          scanned: result.scanned,
          violations: bad,
          unaudited: result.unaudited,
          meta: result.meta,
          error: null,
        }
        totalViolations += bad.length
        totalUnaudited += result.unaudited.length
      } catch (error) {
        entry = { name: page.name, url: page.url, error: error.message }
        report.pages.push(entry)
        throw new Error(`页面审计失败 [${page.name}]: ${error.message}`)
      }

      report.pages.push(entry)
      if (!opts.quiet) {
        const head = `=== ${entry.name} === 扫描 ${entry.scanned} 个文字节点 · 违规 ${entry.violations.length} · 未评估 ${entry.unaudited.length}`
        console.log(`\n${head}`)
        for (const v of entry.violations.slice(0, 12)) {
          console.log(`  ${String(v.ratio).padStart(5)} <${v.need}  ${v.size}px  ${v.sel}`)
          console.log(`        「${v.text}」 fg=${v.fg} bg=${v.bg}`)
        }
        if (entry.violations.length > 12) console.log(`  … 另有 ${entry.violations.length - 12} 处违规`)
        for (const u of entry.unaudited.slice(0, 6)) {
          console.log(`  [未评估] ${u.reason}  ${u.sel}  「${u.text}」`)
        }
        if (entry.unaudited.length > 6) console.log(`  … 另有 ${entry.unaudited.length - 6} 处未评估`)
      }
    }

    report.summary = { violations: totalViolations, unaudited: totalUnaudited, pages: report.pages.length }
    if (!opts.quiet) {
      console.log(
        `\n总计：${report.pages.length} 页 · 违规 ${totalViolations} · 未评估 ${totalUnaudited}` +
          (opts.min !== null ? `（统一阈值 ${opts.min}）` : '（AA：正文 4.5 / 大字 3.0）'),
      )
    }

    if (opts.json) writeFileSync(opts.json, `${JSON.stringify(report, null, 2)}\n`, 'utf-8')

    if (totalViolations > 0) return EXIT.VIOLATION
    if (totalUnaudited > 0) return EXIT.UNAUDITED
    return EXIT.PASS
  } catch (error) {
    report.error = error.message
    if (opts.json) {
      try {
        writeFileSync(opts.json, `${JSON.stringify(report, null, 2)}\n`, 'utf-8')
      } catch {
        /* ignore */
      }
    }
    console.error(`\n审计中断：${error.message}`)
    return EXIT.EXECUTION
  } finally {
    cdp?.close()
    if (chrome) {
      try {
        chrome.kill()
      } catch {
        /* 可能已经退出 */
      }
      // 等进程真正退出，避免留下孤儿进程与端口占用
      for (let i = 0; i < 40 && chrome.exitCode === null; i += 1) await sleep(50)
      if (chrome.exitCode === null) {
        try {
          process.kill(chrome.pid, 'SIGKILL')
        } catch {
          /* 已被回收：ESRCH 属于正常竞态，不能让清理失败覆盖退出码 */
        }
      }
    }
  }
}

main()
  .then((code) => {
    const label = code === 0 ? 'PASS' : code === 1 ? 'FAIL(violations)' : code === 2 ? 'FAIL(execution)' : 'FAIL(unaudited)'
    console.log(`\n${label} exit=${code}`)
    process.exit(code)
  })
  .catch((error) => {
    console.error(`审计崩溃：${error.stack ?? error.message}`)
    process.exit(EXIT.EXECUTION)
  })
