/**
 * 真实 Tauri / WebView2 验收：附着到已启动的 WebView2（CDP 端口 9223），
 * 读数 + 操作 + 截图。窗口由外部启动，脚本不负责拉起进程。
 *
 * 启动方式（PowerShell / bash）：
 *   WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=9223" \
 *     frontend/src-tauri/target/release/yijing-workbench.exe
 *
 * 用法：
 *   node scripts/webview2-check.mjs --phase=inspect
 *   node scripts/webview2-check.mjs --phase=persistence
 *
 * 退出码：0 通过；1 断言失败；2 无法连接。
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { setTimeout as sleep } from 'node:timers/promises'

const PORT = Number(process.env.WEBVIEW2_PORT ?? 9223)
const OUT_DIR = 'docs/review/design-r2/after'
const STATE = 'docs/review/design-r2/checks/webview2-state.json'
const phase = (process.argv.find((a) => a.startsWith('--phase=')) ?? '--phase=inspect').split('=')[1]

const results = []
function check(name, ok, detail = '') {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`)
}

class Cdp {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else resolve(msg.result)
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
  async evaluate(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression: `(async () => { ${expression} })()`,
      returnByValue: true,
      awaitPromise: true,
      userGesture: true,
    })
    if (res.exceptionDetails) throw new Error(res.exceptionDetails.exception?.description ?? res.exceptionDetails.text)
    return res.result.value
  }
  async shot(file) {
    const { data } = await this.send('Page.captureScreenshot', { format: 'png' })
    writeFileSync(`${OUT_DIR}/${file}`, Buffer.from(data, 'base64'))
  }
}

async function attach() {
  let base = null
  for (let i = 0; i < 60 && !base; i += 1) {
    for (const host of ['127.0.0.1', '[::1]']) {
      try {
        const res = await fetch(`http://${host}:${PORT}/json/list`)
        if (res.ok) {
          const list = await res.json()
          const page = list.find((t) => t.type === 'page' && t.webSocketDebuggerUrl)
          if (page) {
            base = page.webSocketDebuggerUrl
            break
          }
        }
      } catch {
        /* retry */
      }
    }
    if (!base) await sleep(300)
  }
  if (!base) throw new Error(`无法连接 WebView2 CDP（端口 ${PORT}），应用是否已用 --remote-debugging-port 启动？`)
  const ws = new WebSocket(base)
  await new Promise((ok, bad) => {
    ws.addEventListener('open', ok, { once: true })
    ws.addEventListener('error', () => bad(new Error('WebSocket 连接失败')), { once: true })
  })
  const cdp = new Cdp(ws)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  return cdp
}

async function main() {
  const cdp = await attach()
  try {
    const env = await cdp.evaluate(`
      return {
        ua: navigator.userAgent,
        dpr: window.devicePixelRatio,
        size: [window.innerWidth, window.innerHeight],
        theme: document.documentElement.dataset.theme,
        colorScheme: getComputedStyle(document.documentElement).colorScheme,
        bodyBg: getComputedStyle(document.body).backgroundColor,
        stored: localStorage.getItem('yijing-appearance'),
        hasShell: !!document.querySelector('.app-shell'),
      };
    `)

    if (phase === 'inspect') {
      check('运行在真实 WebView2（UA 含 Edg/）', env.ua.includes('Edg/'), env.ua.slice(0, 82))
      check('应用已挂载（非白屏）', env.hasShell === true, `viewport=${env.size.join('x')} dpr=${env.dpr}`)
      check('首启为浅色（无存储偏好）', env.theme === 'light' && env.stored === null, `theme=${env.theme} stored=${env.stored}`)
      await cdp.shot('webview2-home-light.png')

      // 顶栏按钮切到夜间
      const afterToggle = await cdp.evaluate(`
        document.querySelector('.appearance-toggle').click();
        await new Promise((r) => setTimeout(r, 450));
        return {
          theme: document.documentElement.dataset.theme,
          darkClass: document.documentElement.classList.contains('dark'),
          stored: localStorage.getItem('yijing-appearance'),
          bodyBg: getComputedStyle(document.body).backgroundColor,
          sidebarBg: getComputedStyle(document.querySelector('.app-sidebar')).backgroundColor,
          fontBase: getComputedStyle(document.body).fontSize,
        };
      `)
      check('点击顶栏按钮切到夜间', afterToggle.theme === 'dark' && afterToggle.darkClass === true, JSON.stringify(afterToggle))
      check('主题写入 localStorage', afterToggle.stored === 'dark', String(afterToggle.stored))
      await cdp.shot('webview2-home-dark.png')

      // 起卦 → 结果页
      const cast = await cdp.evaluate(`
        const el = document.querySelector('#question');
        const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
        set.call(el, 'WebView2 实机验收：夜间模式下这一版的层级是否稳定？');
        el.dispatchEvent(new Event('input', { bubbles: true }));
        document.querySelector('.cast-button').click();
        await new Promise((r) => setTimeout(r, 1800));
        return {
          heading: document.querySelector('.result-heading h1')?.textContent.trim() ?? null,
          tabs: document.querySelectorAll('.result-tabs button').length,
          cardBg: document.querySelector('.hexagram-card') ? getComputedStyle(document.querySelector('.hexagram-card')).backgroundColor : null,
          lineColor: document.querySelector('.gua-line__segment') ? getComputedStyle(document.querySelector('.gua-line__segment')).backgroundColor : null,
        };
      `)
      check('实机起卦并渲染结果页', cast.tabs === 4 && Boolean(cast.heading), JSON.stringify({ tabs: cast.tabs, heading: cast.heading?.slice(0, 18) }))
      await cdp.shot('webview2-result-dark.png')

      // 结果页 → 排盘 → 生成
      const najia = await cdp.evaluate(`
        [...document.querySelectorAll('.result-tabs button')][2].click();
        await new Promise((r) => setTimeout(r, 900));
        const gen = [...document.querySelectorAll('.najia-controls .el-button')].find((b) => b.textContent.includes('生成'));
        gen?.click();
        await new Promise((r) => setTimeout(r, 1800));
        return { rows: document.querySelectorAll('.najia-table tbody tr').length, bg: document.querySelector('.najia-table thead th') ? getComputedStyle(document.querySelector('.najia-table thead th')).backgroundColor : null };
      `)
      check('实机排盘表格生成 6 爻', najia.rows === 6, JSON.stringify(najia))
      await cdp.shot('webview2-najia-dark.png')

      // 历史 → 删除确认（el-message-box 实机）
      const confirmBox = await cdp.evaluate(`
        document.querySelector('.bottom-nav button:nth-child(3)')?.click();
        const historyBtn = [...document.querySelectorAll('.side-nav__item')].find((b) => b.textContent.includes('历史'));
        historyBtn?.click();
        await new Promise((r) => setTimeout(r, 1200));
        document.querySelector('.history-more summary')?.click();
        await new Promise((r) => setTimeout(r, 300));
        document.querySelector('.history-more button')?.click();
        await new Promise((r) => setTimeout(r, 800));
        const box = [...document.querySelectorAll('.el-message-box')].find((el) => el.offsetParent !== null);
        if (!box) return { present: false };
        const parse = (v) => { const t = String(v); const i = t.indexOf('('); const n = t.slice(i + 1, t.lastIndexOf(')')).split(',').map((x) => Number(x.trim())); return { r: n[0], g: n[1], b: n[2] }; };
        const lum = (c) => { const f = (v) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
        const bg = parse(getComputedStyle(box).backgroundColor);
        const fg = parse(getComputedStyle(box.querySelector('.el-message-box__title') ?? box).color);
        const a = lum(bg), b = lum(fg);
        return {
          present: true,
          bg: getComputedStyle(box).backgroundColor,
          lum: Math.round(a * 1000) / 1000,
          titleContrast: Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 100) / 100,
          teleported: box.closest('.el-overlay')?.parentElement === document.body,
        };
      `)
      check('实机 message-box 打开且为暗色表面', confirmBox.present === true && (confirmBox.lum ?? 1) < 0.12, JSON.stringify(confirmBox))
      check('实机 message-box 标题对比 ≥ 4.5', (confirmBox.titleContrast ?? 0) >= 4.5, String(confirmBox.titleContrast))
      await cdp.shot('webview2-messagebox-dark.png')

      writeFileSync(STATE, `${JSON.stringify({ env, afterToggle, cast, najia, confirmBox }, null, 2)}\n`, 'utf-8')
    } else {
      check('重启后仍为夜间（持久化）', env.theme === 'dark', `theme=${env.theme} stored=${env.stored}`)
      check('重启后仍是真实 WebView2', env.ua.includes('Edg/'), env.ua.slice(0, 60))
      await cdp.shot('webview2-restart-dark.png')
    }

    const failed = results.filter((r) => !r.ok)
    console.log(`\n${results.length - failed.length}/${results.length} 通过（phase=${phase}）`)
    return failed.length === 0 ? 0 : 1
  } finally {
    try {
      cdp.ws.close()
    } catch {
      /* ignore */
    }
  }
}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    console.error(`执行失败：${error.message}`)
    process.exit(2)
  })
