/**
 * 无依赖截图器：直接驱动 Chrome DevTools Protocol。
 * Node 22 自带全局 WebSocket，因此不需要 puppeteer。
 *
 * 用法：
 *   node scripts/shoot.mjs shots.json
 * shots.json 是数组，每项：
 *   { "url": "...", "out": "path.png", "width": 1440, "height": 900,
 *     "full": true, "dark": false, "scroll": 0, "wait": 800,
 *     "prepare": "document.querySelector('.x')?.click()" }
 */
import { spawn } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PORT = 9333
const profile = `${process.env.TEMP ?? '.'}\\yijing-shots-profile`

const shots = JSON.parse(readFileSync(process.argv[2], 'utf8'))

const chrome = spawn(
  CHROME,
  [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    '--force-device-scale-factor=1',
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
    ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve: ok, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else ok(msg.result)
      } else if (msg.method) {
        for (const fn of this.listeners.get(msg.method) ?? []) fn(msg.params)
      }
    })
  }

  send(method, params = {}) {
    const id = (this.id += 1)
    return new Promise((ok, reject) => {
      this.pending.set(id, { resolve: ok, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }

  once(method) {
    return new Promise((ok) => {
      const list = this.listeners.get(method) ?? []
      const fn = (params) => {
        this.listeners.set(method, (this.listeners.get(method) ?? []).filter((f) => f !== fn))
        ok(params)
      }
      this.listeners.set(method, [...list, fn])
    })
  }
}

async function connect() {
  const res = await fetch(`${devtoolsBase}/json/new?about:blank`, { method: 'PUT' })
  const target = await res.json()
  const ws = new WebSocket(target.webSocketDebuggerUrl)
  await new Promise((ok, bad) => {
    ws.addEventListener('open', ok, { once: true })
    ws.addEventListener('error', bad, { once: true })
  })
  return new Cdp(ws)
}

await waitForDevtools()
const cdp = await connect()
await cdp.send('Page.enable')
await cdp.send('Runtime.enable')

for (const shot of shots) {
  const { url, out, width = 1440, height = 900, full = false, dark = false, wait = 900, scale = 1 } = shot
  const goto = async (target, ms) => {
    const loaded = cdp.once('Page.loadEventFired')
    await cdp.send('Page.navigate', { url: target })
    // 同文档的 hash 跳转不会触发 loadEventFired，这里加超时兜底
    await Promise.race([loaded.catch(() => {}), sleep(8000)])
    await sleep(ms)
  }

  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: scale,
    mobile: width < 520,
  })
  await goto(url, wait)

  // 主题走真实路径：写 localStorage 后强制重载，图标与色板一起切换
  await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      try {
        if (${dark}) {
          localStorage.setItem('yijing-theme', 'dark');
          localStorage.setItem('yijing-appearance', 'dark');
        } else {
          localStorage.removeItem('yijing-theme');
          localStorage.removeItem('yijing-appearance');
        }
      } catch (e) {}
      return true;
    })()`,
  })
  const reloaded = cdp.once('Page.loadEventFired')
  await cdp.send('Page.reload', { ignoreCache: true })
  await Promise.race([reloaded.catch(() => {}), sleep(8000)])
  await sleep(wait)
  if (shot.prepare) {
    await cdp.send('Runtime.evaluate', { expression: shot.prepare, awaitPromise: true })
    await sleep(1200)
  }
  if (shot.scroll) {
    await cdp.send('Runtime.evaluate', {
      expression: `window.scrollTo(0, ${Number(shot.scroll)})`,
    })
    await sleep(300)
  }

  const params = { format: 'png', captureBeyondViewport: full }
  if (shot.region) {
    // 局部放大：按视口坐标裁剪，配合 scale 做 2x 细节图
    params.clip = { ...shot.region, scale: 1 }
    delete params.captureBeyondViewport
  } else if (full) {
    const metrics = await cdp.send('Page.getLayoutMetrics')
    const content = metrics.cssContentSize ?? metrics.contentSize
    params.clip = {
      x: 0,
      y: 0,
      width: Math.ceil(content.width),
      height: Math.ceil(content.height),
      scale: 1,
    }
  }
  const { data } = await cdp.send('Page.captureScreenshot', params)
  const file = resolve(out)
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, Buffer.from(data, 'base64'))
  console.log(`${out}  ${width}x${full ? params.clip.height : height}`)
}

chrome.kill()
process.exit(0)
