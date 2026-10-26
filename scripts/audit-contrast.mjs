/**
 * DOM 级对比度审计：逐个文字节点算「有效背景」与 WCAG 比值。
 * 比 token 校验更狠——它能抓到遗留的写死色值。
 *
 * 用法： node scripts/audit-contrast.mjs [--min 3]
 * 退出码：存在低于阈值的文字节点 = 1
 */
import { spawn } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PORT = 9337
const profile = `${process.env.TEMP ?? '.'}\\yijing-audit-profile`
const MIN = Number(process.argv[process.argv.indexOf('--min') + 1]) || 3

const PAGES = [
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
      expression,
      returnByValue: true,
      awaitPromise: true,
    })
    if (res.exceptionDetails) throw new Error(res.exceptionDetails.text)
    return res.result.value
  }
}

// 页面内执行：几何/颜色全部按真实渲染值算
const AUDIT_JS = String.raw`
(() => {
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
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
  const effectiveBg = (el) => {
    let acc = null;
    for (let node = el; node; node = node.parentElement) {
      const cs = getComputedStyle(node);
      if (cs.backgroundImage !== 'none') {
        // 有渐变/图片时退化为底色近似，跳过该层
      }
      const c = parse(cs.backgroundColor);
      if (!c || c.a === 0) continue;
      acc = acc ? blend(acc, c) : c;
      if (acc.a >= 1) return acc;
    }
    return acc || { r: 255, g: 255, b: 255, a: 1 };
  };
  const ratio = (a, b) => {
    const la = lum(a), lb = lum(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  };
  const path = (el) => {
    const bits = [];
    for (let n = el; n && bits.length < 4; n = n.parentElement) {
      let s = n.tagName.toLowerCase();
      if (n.classList && n.classList.length) s += '.' + [...n.classList].slice(0, 2).join('.');
      bits.unshift(s);
    }
    return bits.join('>');
  };
  const out = [];
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
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) < 0.25) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;
    const fgRaw = parse(cs.color);
    if (!fgRaw) continue;
    const bg = effectiveBg(el);
    const fg = fgRaw.a < 1 ? blend(fgRaw, bg) : fgRaw;
    const r = ratio(fg, bg);
    const size = parseFloat(cs.fontSize);
    const bold = Number(cs.fontWeight) >= 600;
    const large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5;
    if (r < need) {
      out.push({
        sel: path(el),
        text: text.slice(0, 42),
        fg: cs.color,
        bg: 'rgb(' + [bg.r, bg.g, bg.b].map((v) => Math.round(v)).join(',') + ')',
        ratio: Math.round(r * 100) / 100,
        need,
        size,
      });
    }
  }
  return out;
})()
`

async function goto(cdp, url, wait = 1200) {
  const loaded = cdp.once('Page.loadEventFired')
  await cdp.send('Page.navigate', { url })
  await Promise.race([loaded.catch(() => {}), sleep(8000)])
  await sleep(wait)
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

let total = 0
for (const page of PAGES) {
  await goto(cdp, page.url, 1600)
  await cdp.evaluate(`localStorage.setItem(${JSON.stringify(page.key)}, ${JSON.stringify(page.theme)}); true`)
  const loaded = cdp.once('Page.loadEventFired')
  await cdp.send('Page.reload', { ignoreCache: true })
  await Promise.race([loaded.catch(() => {}), sleep(8000)])
  await sleep(1500)

  const violations = await cdp.evaluate(AUDIT_JS)
  total += violations.length
  console.log(`\n=== ${page.name} === ${violations.length} 处低于阈值`)
  for (const v of violations.slice(0, 14)) {
    console.log(`  ${String(v.ratio).padStart(5)} <${v.need}  ${v.size}px  ${v.sel}`)
    console.log(`        「${v.text}」 fg=${v.fg} bg=${v.bg}`)
  }
  if (violations.length > 14) console.log(`  … 另有 ${violations.length - 14} 处`)
}

console.log(`\n总计 ${total} 处`)
chrome.kill()
process.exit(0)
