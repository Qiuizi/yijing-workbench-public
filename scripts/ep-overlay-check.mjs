/**
 * Element Plus 浮层在深浅两套主题下的实开验收。
 *
 * 打开真实的 dialog / drawer / message-box / select 下拉 / message，
 * 量计算样式（表面色、文字对比度、焦点、遮罩、Teleport、滚动锁），并截图。
 *
 * 用法： node scripts/ep-overlay-check.mjs
 * 前置：桌面端 dev 在 5194（自检页 /dev/overlay-inspect.html）。
 * 退出码：0 全部通过；1 有断言失败；2 执行失败。
 */
import { spawn } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
const PORT = Number(process.env.EP_PORT ?? 9338)
const PROFILE = `${process.env.TEMP ?? '.'}\\yijing-ep-profile`
const BASE = process.env.EP_BASE ?? 'http://127.0.0.1:5194'
const OUT_DIR = 'docs/review/design-r2/after'

const results = []
function check(name, ok, detail = '') {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`)
}

// ---------------- cdp plumbing ----------------
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
      userGesture: true,
    })
    if (res.exceptionDetails) {
      throw new Error(res.exceptionDetails.exception?.description ?? res.exceptionDetails.text)
    }
    return res.result.value
  }

  async shot(file, clip) {
    const params = { format: 'png' }
    if (clip) params.clip = { ...clip, scale: 1 }
    const { data } = await this.send('Page.captureScreenshot', params)
    mkdirSync(OUT_DIR, { recursive: true })
    writeFileSync(`${OUT_DIR}/${file}`, Buffer.from(data, 'base64'))
  }

  close() {
    try {
      this.ws.close()
    } catch {
      /* ignore */
    }
  }
}

// 页面内工具：量计算样式 + 对比度
const PROBE_HELPERS = `
  const parse = (value) => {
    const m = String(value).match(/rgba?\\(([^)]+)\\)/);
    if (!m) return null;
    const parts = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number);
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };
  const lum = (c) => {
    const f = (v) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const blend = (top, bottom) => ({
    r: top.r * top.a + bottom.r * (1 - top.a),
    g: top.g * top.a + bottom.g * (1 - top.a),
    b: top.b * top.a + bottom.b * (1 - top.a),
    a: 1,
  });
  const effBg = (el) => {
    let acc = null;
    for (let n = el; n; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (!c || c.a === 0) continue;
      acc = acc ? blend(acc, c) : c;
      if (acc.a >= 0.999) return acc;
    }
    return acc || { r: 255, g: 255, b: 255, a: 1 };
  };
  const contrast = (el) => {
    const fgRaw = parse(getComputedStyle(el).color);
    const bg = effBg(el);
    const fg = fgRaw.a < 1 ? blend(fgRaw, bg) : fgRaw;
    const a = lum(fg), b = lum(bg);
    return Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 100) / 100;
  };
  const surface = (el) => {
    const bg = effBg(el);
    return { rgb: 'rgb(' + [bg.r, bg.g, bg.b].map((v) => Math.round(v)).join(',') + ')', lum: Math.round(lum(bg) * 1000) / 1000 };
  };
`

async function goto(cdp, url, wait = 1600) {
  const blank = cdp.once('Page.loadEventFired')
  await cdp.send('Page.navigate', { url: 'about:blank' })
  await Promise.race([blank, sleep(2000)])
  const loaded = cdp.once('Page.loadEventFired')
  const nav = await cdp.send('Page.navigate', { url })
  if (nav.errorText) throw new Error(`导航失败: ${nav.errorText}`)
  await Promise.race([loaded, sleep(15000)])
  await sleep(wait)
}

async function waitFor(cdp, selector, timeout = 8000) {
  const started = Date.now()
  while (Date.now() - started < timeout) {
    const ok = await cdp.evaluate(`return !!document.querySelector(${JSON.stringify(selector)})`).catch(() => false)
    if (ok) return true
    await sleep(150)
  }
  const where = await cdp
    .evaluate(`return ({ href: location.href, ready: document.readyState, body: document.body ? document.body.childElementCount : -1 })`)
    .catch((error) => ({ error: error.message }))
  console.error(`  waitFor(${selector}) 超时：${JSON.stringify(where)}`)
  return false
}

async function runTheme(cdp, theme) {
  const url = `${BASE}/dev/overlay-inspect.html?theme=${theme}`
  const expectDark = theme === 'dark'

  // ---- dialog ----
  await goto(cdp, url)
  if (!(await waitFor(cdp, '#btn-dialog'))) throw new Error(`自检页未渲染（${theme}）`)
  await cdp.evaluate(`
    document.querySelector('#btn-dialog').click();
    await new Promise((r) => setTimeout(r, 600));
    const dlg = document.querySelector('.el-dialog');
    const title = document.querySelector('.el-dialog__title');
    const body = document.querySelector('.el-dialog__body p');
    const primary = document.querySelector('.el-dialog__footer .el-button--primary');
    ${PROBE_HELPERS}
    const overlay = document.querySelector('.el-overlay');
    const overlayRect = overlay?.getBoundingClientRect();
    const coversViewport = !!overlayRect && overlayRect.width >= window.innerWidth - 1 && overlayRect.height >= window.innerHeight - 1;
    const positionFixed = overlay ? getComputedStyle(overlay).position === 'fixed' : false;
    const s = surface(dlg);
    return {
      present: !!dlg,
      surface: s.rgb,
      lum: s.lum,
      titleContrast: title ? contrast(title) : null,
      bodyContrast: body ? contrast(body) : null,
      primaryContrast: primary ? contrast(primary) : null,
      primaryBg: primary ? surface(primary).rgb : null,
      coversViewport,
      positionFixed,
      overlayMask: (() => { const o = document.querySelector('.el-overlay'); return o ? getComputedStyle(o).backgroundColor : null; })(),
    }
  `).then((r) => {
    check(`[${theme}] dialog 已打开`, r.present === true)
    check(
      `[${theme}] dialog 表面色符合主题`,
      expectDark ? r.lum < 0.12 : r.lum > 0.75,
      `bg=${r.surface} lum=${r.lum}`,
    )
    check(`[${theme}] dialog 标题/正文对比度 ≥ 4.5`, (r.titleContrast ?? 0) >= 4.5 && (r.bodyContrast ?? 0) >= 4.5, `title=${r.titleContrast} body=${r.bodyContrast}`)
    check(`[${theme}] dialog 主按钮文字 ≥ 4.5`, (r.primaryContrast ?? 0) >= 4.5, `fg/bg=${r.primaryContrast} bg=${r.primaryBg}`)
    check(`[${theme}] dialog 遮罩覆盖视口（fixed）`, r.coversViewport === true && r.positionFixed === true)
    check(`[${theme}] 遮罩存在且有颜色`, Boolean(r.overlayMask) && r.overlayMask !== 'rgba(0, 0, 0, 0)', String(r.overlayMask))
  })
  await cdp.shot(`ep-dialog-${theme}.png`)
  await cdp.evaluate(`document.querySelector('.el-dialog__footer .el-button:not(.el-button--primary)').click(); await new Promise((r) => setTimeout(r, 500)); return true;`)

  // ---- drawer ----
  await cdp.evaluate(`
    document.querySelector('#btn-drawer').click();
    await new Promise((r) => setTimeout(r, 700));
    const drawer = document.querySelector('.el-drawer');
    const body = document.querySelector('.el-drawer__body p');
    const title = document.querySelector('.el-drawer__title');
    ${PROBE_HELPERS}
    const s = surface(drawer);
    return {
      present: !!drawer,
      surface: s.rgb,
      lum: s.lum,
      bodyContrast: body ? contrast(body) : null,
      titleContrast: title ? contrast(title) : null,
      hiddenLock: document.body.className,
    };
  `).then((r) => {
    check(`[${theme}] drawer 已打开`, r.present === true)
    check(`[${theme}] drawer 表面色符合主题`, expectDark ? r.lum < 0.12 : r.lum > 0.75, `bg=${r.surface} lum=${r.lum}`)
    check(`[${theme}] drawer 标题/正文对比度 ≥ 4.5`, (r.titleContrast ?? 0) >= 4.5 && (r.bodyContrast ?? 0) >= 4.5, `title=${r.titleContrast} body=${r.bodyContrast}`)
  })
  await cdp.shot(`ep-drawer-${theme}.png`)
  const drawerClosed = await cdp.evaluate(`
    document.querySelector('.el-drawer__close-btn')?.click();
    await new Promise((r) => setTimeout(r, 700));
    return { hidden: !document.querySelector('.el-drawer') || getComputedStyle(document.querySelector('.el-drawer')).display === 'none', bodyClass: document.body.className };
  `)
  check(`[${theme}] drawer 关闭后释放滚动锁`, !drawerClosed.bodyClass.includes('el-popup-parent--hidden'), drawerClosed.bodyClass || '(none)')

  // ---- message-box ----
  await goto(cdp, url)
  if (!(await waitFor(cdp, '#btn-messagebox'))) throw new Error(`自检页未渲染（${theme}）`)
  await cdp.evaluate(`
    document.querySelector('#btn-messagebox').click();
    await new Promise((r) => setTimeout(r, 700));
    const box = [...document.querySelectorAll('.el-message-box')].find((el) => el.offsetParent !== null) ?? document.querySelector('.el-message-box');
    const msg = box?.querySelector('.el-message-box__message');
    const title = box?.querySelector('.el-message-box__title');
    const confirmBtn = box?.querySelector('.el-message-box__btns .el-button--primary');
    const cancelBtn = box?.querySelector('.el-message-box__btns .el-button:not(.el-button--primary)');
    ${PROBE_HELPERS}
    const s = surface(box);
    return {
      present: !!box,
      surface: s.rgb,
      lum: s.lum,
      titleContrast: title ? contrast(title) : null,
      msgContrast: msg ? contrast(msg) : null,
      confirmContrast: confirmBtn ? contrast(confirmBtn) : null,
      cancelContrast: cancelBtn ? contrast(cancelBtn) : null,
      iconClass: box?.querySelector('.el-message-box__status')?.className ?? null,
      teleported: (() => {
        const boxOverlay = document.querySelector('.el-overlay-message-box')?.closest('.el-overlay');
        return boxOverlay ? boxOverlay.parentElement === document.body : false;
      })(),
    };
  `).then((r) => {
    check(`[${theme}] message-box 已打开`, r.present === true)
    check(`[${theme}] message-box 表面色符合主题`, expectDark ? r.lum < 0.12 : r.lum > 0.75, `bg=${r.surface} lum=${r.lum}`)
    check(
      `[${theme}] message-box 标题/正文/按钮对比度 ≥ 4.5`,
      Math.min(r.titleContrast ?? 0, r.msgContrast ?? 0, r.confirmContrast ?? 0, r.cancelContrast ?? 0) >= 4.5,
      `title=${r.titleContrast} msg=${r.msgContrast} confirm=${r.confirmContrast} cancel=${r.cancelContrast}`,
    )
    check(`[${theme}] message-box Teleport 到 body`, r.teleported === true)
    check(`[${theme}] message-box 警告图标存在`, String(r.iconClass ?? '').includes('warning') || String(r.iconClass ?? '').includes('is-warning'), String(r.iconClass))
  })
  await cdp.shot(`ep-messagebox-${theme}.png`)

  // 已打开的浮层跟随主题切换
  await cdp.evaluate(`
    const root = document.documentElement;
    const boxEl = [...document.querySelectorAll('.el-message-box')].find((el) => el.offsetParent !== null);
    const before = getComputedStyle(boxEl).backgroundColor;
    root.dataset.theme = '${expectDark ? 'light' : 'dark'}';
    root.classList.toggle('dark', ${expectDark ? 'false' : 'true'});
    root.style.colorScheme = '${expectDark ? 'light' : 'dark'}';
    await new Promise((r) => setTimeout(r, 400));
    const after = getComputedStyle(boxEl).backgroundColor;
    return { before, after };
  `).then((r) => {
    check(`[${theme}] 浮层跟随主题切换`, r.before !== r.after, `${r.before} → ${r.after}`)
  })
  await cdp.shot(`ep-messagebox-switched-from-${theme}.png`)
  await cdp.evaluate(`
    [...document.querySelectorAll('.el-message-box')].find((el) => el.offsetParent !== null)?.querySelector('.el-message-box__btns .el-button:not(.el-button--primary)')?.click();
    await new Promise((r) => setTimeout(r, 500));
    return true;
  `)

  // ---- select 下拉 ----
  await goto(cdp, url)
  if (!(await waitFor(cdp, '#probe-select'))) throw new Error(`选择器未渲染（${theme}）`)
  await cdp.evaluate(`
    const selectRoot = document.querySelector('#probe-select');
    (selectRoot.querySelector('.el-select__wrapper') ?? selectRoot).click();
    await new Promise((r) => setTimeout(r, 600));
    const popper = document.querySelector('.el-select__popper');
    const items = [...document.querySelectorAll('.el-select-dropdown__item')];
    ${PROBE_HELPERS}
    const s = popper ? surface(popper.querySelector('.el-select-dropdown')) : null;
    const selected = items.find((i) => i.classList.contains('is-selected'));
    const normal = items.find((i) => !i.classList.contains('is-selected'));
    return {
      present: !!popper,
      surface: s?.rgb ?? null,
      lum: s?.lum ?? null,
      count: items.length,
      itemContrast: items.length ? contrast(items[0]) : null,
      selectedBg: selected ? getComputedStyle(selected).backgroundColor : null,
      normalBg: normal ? getComputedStyle(normal).backgroundColor : null,
      popperParent: popper ? !document.querySelector('.harness')?.contains(popper) : false,
      popperHost: popper?.parentElement?.id || popper?.parentElement?.tagName || null,
    };
  `).then((r) => {
    check(`[${theme}] select 下拉已展开`, r.present === true && r.count >= 3, `items=${r.count}`)
    check(`[${theme}] select 下拉表面色符合主题`, expectDark ? (r.lum ?? 1) < 0.12 : (r.lum ?? 0) > 0.75, `bg=${r.surface} lum=${r.lum}`)
    check(`[${theme}] select 选项文字 ≥ 4.5`, (r.itemContrast ?? 0) >= 4.5, `contrast=${r.itemContrast}`)
    check(`[${theme}] select 选中项与普通项可区分`, r.selectedBg !== r.normalBg, `selected=${r.selectedBg} normal=${r.normalBg}`)
    check(`[${theme}] select 下拉已 Teleport 出组件子树`, r.popperParent === true, String(r.popperHost))
  })
  await cdp.shot(`ep-select-${theme}.png`)
  const hover = await cdp.evaluate(`
    const item = [...document.querySelectorAll('.el-select-dropdown__item')][1];
    const before = getComputedStyle(item).backgroundColor;
    item.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    item.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
    item.classList.add('is-hovering');
    await new Promise((r) => setTimeout(r, 200));
    const after = getComputedStyle(item).backgroundColor;
    return { before, after };
  `)
  check(`[${theme}] select 悬停态可区分`, hover.before !== hover.after, `${hover.before} → ${hover.after}`)
  await cdp.shot(`ep-select-hover-${theme}.png`)

  // ---- message ----
  await goto(cdp, url)
  if (!(await waitFor(cdp, '#btn-message-ok'))) throw new Error(`自检页未渲染（${theme}）`)
  await cdp.evaluate(`
    document.querySelector('#btn-message-ok').click();
    await new Promise((r) => setTimeout(r, 500));
    const el = document.querySelector('.el-message');
    ${PROBE_HELPERS}
    const s = el ? surface(el) : null;
    return { present: !!el, surface: s?.rgb ?? null, lum: s?.lum ?? null, contrast: el ? contrast(el) : null };
  `).then((r) => {
    check(`[${theme}] message 已弹出`, r.present === true)
    check(`[${theme}] message 表面色符合主题`, expectDark ? (r.lum ?? 1) < 0.12 : (r.lum ?? 0) > 0.75, `bg=${r.surface} lum=${r.lum}`)
    check(`[${theme}] message 文字 ≥ 4.5`, (r.contrast ?? 0) >= 4.5, `contrast=${r.contrast}`)
  })
  await cdp.shot(`ep-message-${theme}.png`)

  // ---- 焦点、禁用、单选/复选 ----
  await goto(cdp, url)
  if (!(await waitFor(cdp, '#probe-focus'))) throw new Error(`表单状态未渲染（${theme}）`)
  // 真键盘：先聚焦输入框，再按 Tab 走到按钮 —— 这样才会命中 :focus-visible
  await cdp.evaluate("const input = document.querySelector('#probe-input input') ?? document.querySelector('#probe-input'); input?.focus(); return true;")
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 })
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 })
  await sleep(250)
  const states = await cdp.evaluate(`
    const btn = document.querySelector('#probe-focus');
    const active = document.activeElement;
    ${PROBE_HELPERS}
    const cs = getComputedStyle(btn);
    const radioChecked = document.querySelector('.el-radio-button.is-active .el-radio-button__inner');
    const checkbox = document.querySelector('#probe-checkbox')?.closest('.el-checkbox')?.querySelector('.el-checkbox__inner') ?? document.querySelector('.el-checkbox__inner');
    const disabledBtn = [...document.querySelectorAll('.el-button')].find((b) => b.disabled);
    const disabledSelect = document.querySelector('.el-select__wrapper.is-disabled');
    return {
      activeId: active ? (active.id || active.tagName) : null,
      focusVisible: active && active.matches ? active.matches(':focus-visible') : null,
      outlineWidth: cs.outlineWidth,
      outlineStyle: cs.outlineStyle,
      outlineColor: cs.outlineColor,
      ringContrast: (() => {
        const parse = (v) => { const t = String(v); const i = t.indexOf('('); if (i < 0) return null; const n = t.slice(i + 1, t.lastIndexOf(')')).split(',').map((x) => Number(x.trim())); if (n.length < 3 || n.some((x) => Number.isNaN(x))) return null; return { r: n[0] / 255, g: n[1] / 255, b: n[2] / 255 }; };
        const ring = parse(cs.outlineColor);
        const page = parse(getComputedStyle(document.documentElement).backgroundColor) || parse(getComputedStyle(document.body).backgroundColor);
        if (!ring || !page) return null;
        const lin = (c) => { const f = (v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)); return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
        const a = lin(ring), b = lin(page);
        return Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 100) / 100;
      })(),
      focusContrast: contrast(btn),
      radioBg: radioChecked ? getComputedStyle(radioChecked).backgroundColor : null,
      radioFg: radioChecked ? getComputedStyle(radioChecked).color : null,
      radioContrast: radioChecked ? contrast(radioChecked) : null,
      checkboxBg: checkbox ? getComputedStyle(checkbox).backgroundColor : null,
      disabledOpacity: disabledBtn ? getComputedStyle(disabledBtn).opacity : null,
      disabledContrast: disabledBtn ? contrast(disabledBtn) : null,
      disabledSelectContrast: disabledSelect ? contrast(disabledSelect) : null,
    };
  `)
  check(`[${theme}] 焦点环与页面底对比 ≥ 3`, (states.ringContrast ?? 0) >= 3, `ring=${states.outlineColor} ratio=${states.ringContrast}`)
  check(
    `[${theme}] 键盘焦点可见`,
    states.focusVisible === true && parseFloat(states.outlineWidth) >= 1 && states.outlineStyle !== 'none',
    `active=${states.activeId} focus-visible=${states.focusVisible} outline=${states.outlineWidth} ${states.outlineStyle} ${states.outlineColor}`,
  )
  check(`[${theme}] 按钮文字对比度 ≥ 4.5`, states.focusContrast >= 4.5, String(states.focusContrast))
  check(`[${theme}] 单选选中态对比度 ≥ 4.5`, (states.radioContrast ?? 0) >= 4.5, `${states.radioFg} on ${states.radioBg} = ${states.radioContrast}`)
  check(`[${theme}] 禁用按钮仍可读（≥ 3.0）`, (states.disabledContrast ?? 0) >= 3.0, String(states.disabledContrast))
  check(`[${theme}] 禁用选择器占位符可读（≥ 3.0）`, (states.disabledSelectContrast ?? 0) >= 3.0, String(states.disabledSelectContrast))
  check(`[${theme}] 复选框已勾选`, Boolean(states.checkboxBg) && states.checkboxBg !== 'rgba(0, 0, 0, 0)', String(states.checkboxBg))
  await cdp.shot(`ep-states-${theme}.png`)
}

async function main() {
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
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1100, height: 720, deviceScaleFactor: 1, mobile: false })

    // 先确认自检页真的挂载了，避免把 404 / 白屏当成通过
    await goto(cdp, `${BASE}/dev/overlay-inspect.html`, 1200)
    const probe = await cdp.evaluate(`
      return {
        title: document.title,
        mounted: document.querySelector('.harness') !== null,
        buttons: document.querySelectorAll('.probe').length,
      };
    `)
    if (!probe.mounted || probe.buttons < 6) {
      throw new Error(`自检页未挂载（title=${probe.title} buttons=${probe.buttons}），先启动 vite dev`)
    }

    await runTheme(cdp, 'light')
    await runTheme(cdp, 'dark')

    const failed = results.filter((r) => !r.ok)
    console.log(`\n${results.length - failed.length}/${results.length} 通过`)
    return failed.length === 0 ? 0 : 1
  } catch (error) {
    console.error(`\n执行失败：${error.message}`)
    return 2
  } finally {
    cdp?.close()
    try {
      chrome.kill()
    } catch {
      /* ignore */
    }
  }
}

main().then((code) => process.exit(code))
