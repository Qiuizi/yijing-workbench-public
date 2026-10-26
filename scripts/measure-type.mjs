/**
 * 字号核对：同一元素在浅色 / 夜间下的计算字号，验证「夜间降一档」。
 * 用法： node scripts/measure-type.mjs
 * 前置：官网 dev 5191、桌面端 dev 5194。
 */
import { spawn } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PORT = 9336
const profile = `${process.env.TEMP ?? '.'}\\yijing-measure-profile`

const TARGETS = {
  site: {
    url: 'http://localhost:5191/yijing-workbench-public/',
    key: 'yijing-theme',
    selectors: {
      'hero h1': '.hero h1',
      'hero slogan': '.hero__slogan',
      'hero body': '.hero__sub',
      'section h2': '.section-head h2',
      'section body': '.section-head p',
      'card title': '.feature h3',
      'card body': '.feature p',
      'nav link': '.nav-desktop a',
    },
  },
  app: {
    url: 'http://127.0.0.1:5194/',
    key: 'yijing-appearance',
    selectors: {
      'page title': '.casting-start h1',
      'field label': '.casting-start .field-label',
      'textarea': '.el-textarea__inner',
      'hint': '.field-hint',
      'nav item': '.side-nav__item span',
      'topbar': '.topbar__section',
    },
  },
  learning: {
    url: 'http://127.0.0.1:5194/#/learning',
    key: 'yijing-appearance',
    selectors: {
      'index h1': '.learning-index__heading h1',
      'matrix name': '.learning-matrix__entry > strong',
      'preview title': '.learning-preview__heading h2',
      'preview body': '.learning-preview__original > p',
    },
  },
}

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

let base = null
async function waitForDevtools() {
  for (let i = 0; i < 120; i += 1) {
    for (const host of ['[::1]', '127.0.0.1']) {
      try {
        const res = await fetch(`http://${host}:${PORT}/json/version`)
        if (res.ok) {
          base = `http://${host}:${PORT}`
          return
        }
      } catch {
        /* retry */
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
      expression: `(() => { ${expression} })()`,
      returnByValue: true,
      awaitPromise: true,
    })
    if (res.exceptionDetails) throw new Error(res.exceptionDetails.text)
    return res.result.value
  }
}

async function goto(cdp, url, wait = 900) {
  const loaded = cdp.once('Page.loadEventFired')
  await cdp.send('Page.navigate', { url })
  await Promise.race([loaded.catch(() => {}), sleep(8000)])
  await sleep(wait)
}

async function measure(cdp, selectors) {
  const expr = `
    const out = {};
    for (const [label, sel] of Object.entries(${JSON.stringify(selectors)})) {
      const el = document.querySelector(sel);
      out[label] = el ? parseFloat(getComputedStyle(el).fontSize) : null;
    }
    return out;
  `
  return cdp.evaluate(expr)
}

await waitForDevtools()
const target = await (await fetch(`${base}/json/new?about:blank`, { method: 'PUT' })).json()
const ws = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((ok, bad) => {
  ws.addEventListener('open', ok, { once: true })
  ws.addEventListener('error', bad, { once: true })
})
const cdp = new Cdp(ws)
await cdp.send('Page.enable')
await cdp.send('Runtime.enable')
await cdp.send('Emulation.setDeviceMetricsOverride', {
  width: 1440,
  height: 1000,
  deviceScaleFactor: 1,
  mobile: false,
})

for (const [name, cfg] of Object.entries(TARGETS)) {
  await goto(cdp, cfg.url, 1500)
  const rows = {}
  for (const theme of ['light', 'dark']) {
    await cdp.evaluate(`localStorage.setItem(${JSON.stringify(cfg.key)}, ${JSON.stringify(theme)}); return true;`)
    const loaded = cdp.once('Page.loadEventFired')
    await cdp.send('Page.reload', { ignoreCache: true })
    await Promise.race([loaded.catch(() => {}), sleep(8000)])
    await sleep(1200)
    rows[theme] = await measure(cdp, cfg.selectors)
  }
  console.log(`\n=== ${name} ===`)
  console.log('元素'.padEnd(16), '浅色', '夜间', '差')
  for (const label of Object.keys(cfg.selectors)) {
    const l = rows.light[label]
    const d = rows.dark[label]
    const delta = l != null && d != null ? (d - l).toFixed(1) : '—'
    console.log(String(label).padEnd(16), String(l ?? 'n/a').padEnd(6), String(d ?? 'n/a').padEnd(6), delta)
  }
}

chrome.kill()
process.exit(0)
