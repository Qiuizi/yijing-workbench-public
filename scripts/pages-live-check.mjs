/**
 * 线上 GitHub Pages 验收：中英首页、主题切换与持久化、移动端导航、
 * 图鉴/图库/下载区、控制台错误。截图存 docs/review/design-r2/after/pages-*.png。
 *
 * 用法： node scripts/pages-live-check.mjs
 * 退出码：0 通过；1 断言失败；2 执行失败
 */
import { spawn } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PORT = Number(process.env.PAGES_PORT ?? 9342)
const PROFILE = `${process.env.TEMP ?? '.'}\\yijing-pages-profile`
const SITE = 'https://qiuizi.github.io/yijing-workbench-public/'
const OUT = 'docs/review/design-r2/after'

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
    this.listeners = new Map()
    this.consoleErrors = []
    ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else resolve(msg.result)
      } else if (msg.method) {
        if (msg.method === 'Runtime.exceptionThrown') this.consoleErrors.push(msg.params.exceptionDetails?.text ?? 'exception')
        if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
          this.consoleErrors.push(msg.params.args.map((a) => a.value ?? a.description ?? '').join(' '))
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
    mkdirSync(OUT, { recursive: true })
    writeFileSync(`${OUT}/${file}`, Buffer.from(data, 'base64'))
  }
}

async function goto(cdp, url, wait = 2200) {
  const loaded = cdp.once('Page.loadEventFired')
  const nav = await cdp.send('Page.navigate', { url })
  if (nav.errorText) throw new Error(`导航失败: ${nav.errorText}`)
  await Promise.race([loaded, sleep(25000)])
  await sleep(wait)
}

async function main() {
  const chrome = spawn(
    CHROME,
    ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', `--user-data-dir=${PROFILE}`, `--remote-debugging-port=${PORT}`, 'about:blank'],
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
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })

    // 清掉上一轮残留的 localStorage，保证「首屏为浅色」是可复现的干净起点
    await cdp.send('Storage.clearDataForOrigin', {
      origin: 'https://qiuizi.github.io',
      storageTypes: 'local_storage',
    })

    // ---- 中文首页 ----
    await goto(cdp, SITE)
    const home = await cdp.evaluate(`
      return {
        title: document.title,
        lang: document.documentElement.lang,
        theme: document.documentElement.dataset.theme,
        hasNewBrand: !!document.querySelector('.brand-mark'),
        hasToggle: !!document.querySelector('.theme-toggle'),
        blendSections: document.querySelectorAll('.section--blend').length,
        atlas: document.querySelectorAll('.atlas__grid .cell').length,
        thumbs: document.querySelectorAll('.gallery__thumb').length,
        displayToken: getComputedStyle(document.documentElement).getPropertyValue('--t-display').trim(),
      };
    `)
    check('线上中文首页可加载', home.title.includes('易经起卦工作台') && home.lang === 'zh-CN', `${home.title} / ${home.lang}`)
    check('新版品牌标记与主题按钮已上线', home.hasNewBrand && home.hasToggle, `brand=${home.hasNewBrand} toggle=${home.hasToggle}`)
    check('色阶咬合区块已上线', home.blendSections >= 4, `sections=${home.blendSections}`)
    check('图鉴 64 格 / 图库 9 张', home.atlas === 64 && home.thumbs === 9, `atlas=${home.atlas} thumbs=${home.thumbs}`)
    check('首屏为浅色（无存储偏好）', home.theme === 'light', String(home.theme))
    await cdp.shot('pages-home-light.png')

    // ---- 主题切换 + 刷新持久化 ----
    await cdp.evaluate(`document.querySelector('.theme-toggle').click(); await new Promise((r) => setTimeout(r, 400)); return true;`)
    const dark = await cdp.evaluate(`
      return {
        theme: document.documentElement.dataset.theme,
        stored: localStorage.getItem('yijing-theme'),
        bodyBg: getComputedStyle(document.body).backgroundColor,
        size: getComputedStyle(document.querySelector('.hero__sub')).fontSize,
      };
    `)
    check('线上切换到夜间', dark.theme === 'dark' && dark.stored === 'dark', JSON.stringify(dark))
    await cdp.shot('pages-home-dark.png')
    await cdp.send('Page.reload', { ignoreCache: true })
    await sleep(2600)
    const afterReload = await cdp.evaluate(`return document.documentElement.dataset.theme`)
    check('刷新后仍为夜间（持久化）', afterReload === 'dark', String(afterReload))

    // ---- 下载区数据 ----
    const download = await cdp.evaluate(`
      const tag = document.querySelector('.dl-value')?.textContent.trim();
      const values = [...document.querySelectorAll('.dl-value')].map((n) => n.textContent.trim());
      const name = document.querySelector('.dl-asset-name')?.textContent.trim();
      const size = document.querySelector('.dl-asset-size')?.textContent.trim();
      const sha = document.querySelector('.dl-sha')?.textContent.replace(/\\s+/g, '');
      const href = document.querySelector('.dl-slab__asset a.btn')?.getAttribute('href');
      return { tag, date: values[1] ?? null, name, size, sha, href };
    `)
    check('下载区版本与文件名成对出现', download.tag === 'v3.3.1' && download.name === 'yijing-workbench-3.3.1-x64-setup.exe', JSON.stringify({ tag: download.tag, name: download.name }))
    check('下载链接指向同版本 Release', String(download.href).includes('/releases/download/v3.3.1/'), String(download.href))
    console.log(`  SHA=${download.sha}  size=${download.size}  date=${download.date}`)

    // ---- 移动端 ----
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })
    await goto(cdp, SITE)
    const mobile = await cdp.evaluate(`
      document.querySelector('.nav-toggle')?.click();
      await new Promise((r) => setTimeout(r, 500));
      const drawer = document.querySelector('.mobile-drawer');
      const links = drawer ? drawer.querySelectorAll('nav a').length : 0;
      return {
        toggle: !!document.querySelector('.nav-toggle'),
        open: drawer?.classList.contains('is-open') ?? false,
        links,
        overflow: document.documentElement.scrollWidth <= window.innerWidth + 1,
      };
    `)
    check('移动端抽屉可展开且有 4 个入口', mobile.open === true && mobile.links === 4, JSON.stringify(mobile))
    check('移动端无横向溢出', mobile.overflow === true)
    await cdp.shot('pages-mobile-drawer.png')

    // ---- 英文页 ----
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })
    await goto(cdp, `${SITE}en/`)
    const en = await cdp.evaluate(`
      return {
        lang: document.documentElement.lang,
        h1: document.querySelector('h1')?.textContent.trim(),
        brand: !!document.querySelector('.brand-mark'),
        nav: document.querySelectorAll('.nav-desktop a').length,
      };
    `)
    check('英文首页可加载且带新版品牌区', en.lang === 'en' && en.brand && en.nav === 4, JSON.stringify(en))
    await cdp.shot('pages-en.png')

    const errors = cdp.consoleErrors.filter((e) => !e.includes('favicon'))
    check('线上控制台无错误', errors.length === 0, errors.slice(0, 2).join(' | '))

    const failed = results.filter((r) => !r.ok)
    console.log(`\n${results.length - failed.length}/${results.length} 通过`)
    return failed.length === 0 ? 0 : 1
  } catch (error) {
    console.error(`执行失败：${error.message}`)
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
