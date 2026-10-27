/**
 * 隔离的 Windows NSIS 升级实验（QA 构建，不触碰正式用户数据）。
 *
 * 流程：静默安装旧版 → 造数据（起卦 + 偏好 + 假 API Key）→ 本地 HTTP 源提供新版
 *      → 打开旧版、点「检查更新」「下载并安装」→ 等应用退出、安装器运行、新版起来
 *      → 校验版本 / 历史计数 / 偏好 / DPAPI 密钥 / 备份文件。
 * 额外：篡改安装包后重试，验证签名校验会拒绝安装。
 *
 * 用法：
 *   node scripts/updater/qa-upgrade-e2e.mjs --old-setup <path> --update-dir <dir> [--keep]
 *
 * 前置：--update-dir 里要有 <version>-x64-setup.exe、同名 .sig 和 latest.json。
 * 退出码：0 全部通过；1 有失败；2 执行失败。
 */
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { setTimeout as sleep } from 'node:timers/promises'

const PORT = Number(process.env.QA_WEBVIEW_PORT ?? 9225)
const SERVE_PORT = Number(process.env.QA_SERVE_PORT ?? 8788)
const IDENTIFIER = 'cn.yijing.workbench.updaterqa'
const INSTALL_DIR = join(process.env.LOCALAPPDATA ?? '', 'YijingWorkbenchQA')
const DATA_DIR = join(process.env.LOCALAPPDATA ?? '', IDENTIFIER)
const EXE = join(INSTALL_DIR, 'yijing-workbench.exe')
const OUT_DIR = resolve('docs/updater')
const TMP_DIR = join(process.env.TEMP ?? '.', 'yijing-qa-updater')
mkdirSync(TMP_DIR, { recursive: true })

const args = process.argv.slice(2)
const argOf = (name, fallback = '') => {
  const index = args.indexOf(`--${name}`)
  return index >= 0 ? args[index + 1] : fallback
}
const oldSetup = resolve(argOf('old-setup'))
const updateDir = resolve(argOf('update-dir'))

const results = []
function check(name, ok, detail = '') {
  results.push({ name, ok, detail, at: new Date().toISOString() })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`)
}

function run(command, cmdArgs, options = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, cmdArgs, { stdio: 'ignore', ...options })
    child.on('error', reject)
    child.on('exit', (code) => resolvePromise(code ?? 0))
  })
}

function launchApp(extraEnv = {}) {
  return spawn(EXE, [], {
    env: { ...process.env, WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS: `--remote-debugging-port=${PORT}`, ...extraEnv },
    stdio: 'ignore',
    detached: false,
  })
}

class Cdp {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve: ok, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else ok(msg.result)
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
  async shot(file, clip = null) {
    const params = { format: 'png' }
    if (clip) params.clip = { ...clip, scale: 1 }
    const { data } = await this.send('Page.captureScreenshot', params)
    writeFileSync(join(OUT_DIR, file), Buffer.from(data, 'base64'))
  }
  close() {
    try {
      this.ws.close()
    } catch {
      /* ignore */
    }
  }
}

async function attachCdp(timeoutMs = 40000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    for (const host of ['127.0.0.1', '[::1]']) {
      try {
        const list = await (await fetch(`http://${host}:${PORT}/json/list`)).json()
        const page = list.find((item) => item.type === 'page' && item.webSocketDebuggerUrl)
        if (page) {
          const ws = new WebSocket(page.webSocketDebuggerUrl)
          await new Promise((ok, bad) => {
            ws.addEventListener('open', ok, { once: true })
            ws.addEventListener('error', () => bad(new Error('ws error')), { once: true })
          })
          const cdp = new Cdp(ws)
          await cdp.send('Page.enable')
          await cdp.send('Runtime.enable')
          return cdp
        }
      } catch {
        /* retry */
      }
    }
    await sleep(300)
  }
  throw new Error('WebView2 DevTools 未就绪')
}

async function waitForSelector(cdp, selector, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const found = await cdp.evaluate(`return !!document.querySelector(${JSON.stringify(selector)})`).catch(() => false)
    if (found) return true
    await sleep(250)
  }
  throw new Error(`等待元素超时：${selector}`)
}

async function waitAppExit(child, timeoutMs = 180000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (child.exitCode !== null) return true
    await sleep(500)
  }
  return false
}

// 用 tasklist 的 stdout 判断，避免 cmd 引号与 find 退出码在不同环境下的差异
async function appRunning() {
  const output = await new Promise((ok) => {
    const child = spawn('tasklist', ['/FI', 'IMAGENAME eq yijing-workbench.exe'], {
      stdio: ['ignore', 'pipe', 'ignore'],
    })
    let buffer = ''
    child.stdout.on('data', (chunk) => {
      buffer += chunk.toString()
    })
    child.on('error', () => ok(''))
    child.on('exit', () => ok(buffer))
  })
  return /yijing-workbench\.exe/i.test(output)
}

async function waitProcessGone(timeoutMs = 120000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (!(await appRunning())) return true
    await sleep(700)
  }
  return false
}

async function openUpdatePanel(cdp) {
  return cdp.evaluate(`
    const goSettings = [...document.querySelectorAll('.side-nav__item')].find((b) => b.textContent.includes('设置'))
    goSettings?.click()
    await new Promise((r) => setTimeout(r, 1200))
    const details = [...document.querySelectorAll('details.settings-category')].find((d) => d.textContent.includes('关于应用'))
    details?.setAttribute('open', 'open')
    await new Promise((r) => setTimeout(r, 500))
    document.querySelector('.update-card')?.scrollIntoView({ block: 'center' })
    await new Promise((r) => setTimeout(r, 400))
    return document.documentElement.dataset.theme
  `)
}

async function updatePanelClip(cdp) {
  return cdp.evaluate(`
    const group = document.querySelector('[aria-labelledby="settings-update-title"]')
    if (!group) return null
    const rect = group.getBoundingClientRect()
    // clip 用页面坐标，getBoundingClientRect 是视口坐标，必须加上滚动偏移
    return {
      x: Math.max(0, rect.x + window.scrollX - 12),
      y: Math.max(0, rect.y + window.scrollY - 12),
      width: Math.ceil(rect.width + 24),
      height: Math.ceil(rect.height + 24),
    }
  `)
}

async function captureOnly() {
  if (!existsSync(EXE)) throw new Error(`未安装 QA 版本：${EXE}`)
  mkdirSync(OUT_DIR, { recursive: true })
  const app = launchApp()
  const cdp = await attachCdp()
  await waitForSelector(cdp, '.side-nav__item')
  await cdp.evaluate(`localStorage.setItem('yijing-appearance', 'light'); return true`)
  await cdp.send('Page.reload')
  await sleep(3000)
  await openUpdatePanel(cdp)
  await cdp.shot('update-panel-light.png', await updatePanelClip(cdp))
  const lightTheme = await cdp.evaluate(`return document.documentElement.dataset.theme`)
  await cdp.evaluate(`localStorage.setItem('yijing-appearance', 'dark'); return true`)
  await cdp.send('Page.reload')
  await sleep(3000)
  await openUpdatePanel(cdp)
  await cdp.shot('update-panel-dark.png', await updatePanelClip(cdp))
  const darkTheme = await cdp.evaluate(`return document.documentElement.dataset.theme`)
  cdp.close()
  app.kill()
  console.log(`captured light=${lightTheme} dark=${darkTheme}`)
  return 0
}

async function main() {
  if (args.includes('--capture-only')) return captureOnly()
  if (!oldSetup || !existsSync(oldSetup)) throw new Error(`旧版安装包不存在：${oldSetup}`)
  if (!existsSync(updateDir)) throw new Error(`更新源目录不存在：${updateDir}`)
  mkdirSync(OUT_DIR, { recursive: true })

  // 不做任何删除：以「现有数据为基线」，升级后必须原样保留
  const baseline = await inspectData()
  console.log(`  基线：历史 ${baseline.historyCount} 条（实验只新增，不删除）`)

  // ---------- 1. 安装旧版 ----------
  console.log(`\n[1/7] 静默安装旧版：${oldSetup}`)
  const installCode = await run(oldSetup, ['/S'])
  check('旧版 NSIS 静默安装返回 0', installCode === 0, `exit=${installCode}`)
  check('安装目录存在', existsSync(EXE), EXE)

  // ---------- 2. 造数据 ----------
  console.log('\n[2/7] 启动旧版并造数据（1 条起卦 + 偏好 + 假 API Key）')
  let app = launchApp()
  let cdp = await attachCdp()
  await waitForSelector(cdp, '#question')
  const seeded = await cdp.evaluate(`
    const el = document.querySelector('#question')
    const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set
    set.call(el, '隔离升级实验：更新后这条记录必须还在。')
    el.dispatchEvent(new Event('input', { bubbles: true }))
    document.querySelector('.cast-button').click()
    await new Promise((r) => setTimeout(r, 1800))
    const heading = document.querySelector('.result-heading h1')?.textContent.trim() ?? null

    // 偏好
    const historyBtn = [...document.querySelectorAll('.side-nav__item')].find((b) => b.textContent.includes('设置'))
    historyBtn?.click()
    await new Promise((r) => setTimeout(r, 900))
    const tz = document.querySelector('#default-timezone input') ?? document.querySelector('#default-timezone')
    if (tz) {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      setter.call(tz, 'Asia/Shanghai')
      tz.dispatchEvent(new Event('input', { bubbles: true }))
    }
    const savePref = [...document.querySelectorAll('.settings-preferences-save button')][0]
    savePref?.click()
    await new Promise((r) => setTimeout(r, 800))

    // 假 API Key（走真实 DPAPI 保存路径）
    const keyInput = document.querySelector('#deepseek-key input') ?? document.querySelector('#deepseek-key')
    if (keyInput) {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      setter.call(keyInput, 'sk-qa-updater-e2e-not-a-real-key')
      keyInput.dispatchEvent(new Event('input', { bubbles: true }))
      const saveKey = [...document.querySelectorAll('.settings-field__row button')].find((b) => b.textContent.includes('保存密钥'))
      saveKey?.click()
      await new Promise((r) => setTimeout(r, 1800))
    }
    return { heading, hasKeyInput: !!keyInput }
  `)
  check('旧版起卦成功并渲染结果', Boolean(seeded.heading), String(seeded.heading).slice(0, 24))
  check('设置页可写入 API Key 输入框', seeded.hasKeyInput === true)

  cdp.close()
  app.kill()
  await waitProcessGone(60000)

  const before = await inspectData()
  check('旧版数据：新增 1 条记录', before.historyCount === baseline.historyCount + 1, `${baseline.historyCount} → ${before.historyCount}`)
  check('旧版数据：DPAPI 密钥已保存', before.hasProtectedKey === true)
  check('旧版数据：偏好已写入', before.preferences.includes('Asia/Shanghai'), before.preferences.slice(0, 60))

  // ---------- 3. 本地更新源 ----------
  console.log('\n[3/7] 启动本地更新源')
  const server = createServer((req, res) => {
    const name = decodeURIComponent((req.url ?? '/').replace(/^\//, ''))
    const file = join(updateDir, name)
    if (!existsSync(file)) {
      res.writeHead(404)
      res.end('not found')
      return
    }
    res.writeHead(200, { 'content-type': 'application/octet-stream' })
    res.end(readFileSync(file))
  })
  await new Promise((ok) => server.listen(SERVE_PORT, '127.0.0.1', ok))
  console.log(`  serving ${updateDir} at http://127.0.0.1:${SERVE_PORT}/`)

  // ---------- 4. 检查更新 ----------
  console.log('\n[4/7] 旧版内检查更新')
  app = launchApp()
  cdp = await attachCdp()
  await waitForSelector(cdp, '.side-nav__item')
  const checked = await cdp.evaluate(`
    const goSettings = [...document.querySelectorAll('.side-nav__item')].find((b) => b.textContent.includes('设置'))
    goSettings?.click()
    await new Promise((r) => setTimeout(r, 1200))
    const details = [...document.querySelectorAll('details.settings-category')].find((d) => d.textContent.includes('关于应用'))
    details?.setAttribute('open', 'open')
    await new Promise((r) => setTimeout(r, 400))
    const btn = [...document.querySelectorAll('.update-card button')].find((b) => b.textContent.includes('检查更新'))
    btn?.click()
    await new Promise((r) => setTimeout(r, 3500))
    const group = document.querySelector('[aria-labelledby="settings-update-title"]')
    const card = document.querySelector('.update-card')
    return {
      state: group?.querySelector('.settings-state')?.textContent.trim() ?? null,
      latest: card?.querySelector('.update-release__title')?.textContent.replace(/\\s+/g, ' ').trim() ?? null,
      notes: card?.querySelector('.update-release__notes')?.textContent.trim() ?? null,
    }
  `)
  check('检查更新得到「发现新版本」', checked.state === '发现新版本', `${checked.state} / ${checked.latest}`)
  check('显示可用版本号', String(checked.latest ?? '').includes('3.3.2-qa.2'), String(checked.latest))

  // ---------- 5. 下载并安装 ----------
  console.log('\n[5/7] 下载并安装（应用会退出，安装器接管）')
  const clicked = await cdp.evaluate(`
    const btn = [...document.querySelectorAll('.update-card button')].find((b) => b.textContent.includes('下载并安装'))
    if (!btn) return { clicked: false }
    btn.click()
    return { clicked: true }
  `)
  check('下载并安装按钮可点击', clicked.clicked === true)

  let lastState = null
  let lastError = null
  for (let i = 0; i < 45 && app.exitCode === null; i += 1) {
    const snapshot = await cdp
      .evaluate(`
        const group = document.querySelector('[aria-labelledby="settings-update-title"]')
        const card = document.querySelector('.update-card')
        return {
          state: group?.querySelector('.settings-state')?.textContent.trim() ?? null,
          error: card?.querySelector('.update-error p')?.textContent.trim() ?? null,
          percent: card?.querySelector('.update-progress__meta span')?.textContent.trim() ?? null,
        }
      `)
      .catch(() => null)
    if (snapshot) {
      if (snapshot.state !== lastState) {
        console.log(`  state → ${snapshot.state}${snapshot.percent ? ` (${snapshot.percent})` : ''}`)
        lastState = snapshot.state
      }
      if (snapshot.error) lastError = snapshot.error
    }
    if (app.exitCode !== null) break
    await sleep(2000)
  }
  if (lastError) console.log(`  update error: ${lastError}`)
  const exitedAfterInstall = await waitAppExit(app, 180000)
  check('应用在安装前退出', exitedAfterInstall === true, `lastState=${lastState} error=${lastError ?? '-'}`)
  cdp.close()
  await waitProcessGone(180000)
  await sleep(4000)

  // ---------- 6. 新版本验证 ----------
  console.log('\n[6/7] 验证新版本与数据')
  if (!existsSync(EXE)) throw new Error('安装后找不到可执行文件')
  app = launchApp()
  cdp = await attachCdp()
  await waitForSelector(cdp, '.side-nav__item')
  const after = await cdp.evaluate(`
    const goSettings = [...document.querySelectorAll('.side-nav__item')].find((b) => b.textContent.includes('设置'))
    goSettings?.click()
    await new Promise((r) => setTimeout(r, 1200))
    const details = [...document.querySelectorAll('details.settings-category')].find((d) => d.textContent.includes('关于应用'))
    details?.setAttribute('open', 'open')
    await new Promise((r) => setTimeout(r, 500))
    const group = document.querySelector('[aria-labelledby="settings-update-title"]')
    return {
      aboutVersion: document.querySelector('.settings-about__facts dd')?.textContent.trim() ?? null,
      runtimeVersion: group?.querySelector('.update-card__version strong')?.textContent.trim() ?? null,
      state: group?.querySelector('.settings-state')?.textContent.trim() ?? null,
    }
  `)
  const installedVersion = after.runtimeVersion ?? ''
  check('界面读取到运行时版本 3.3.2-qa.2', String(installedVersion).includes('3.3.2-qa.2'), JSON.stringify(after))
  const dataAfter = await inspectData()
  check('升级后历史记录条数未变', dataAfter.historyCount === before.historyCount, `${before.historyCount} → ${dataAfter.historyCount}`)
  check('升级后问句内容未变', dataAfter.question === '隔离升级实验：更新后这条记录必须还在。', dataAfter.question.slice(0, 30))
  check('升级后偏好保留', dataAfter.preferences.includes('Asia/Shanghai'), dataAfter.preferences.slice(0, 60))
  check('升级后 DPAPI 密钥仍存在', dataAfter.hasProtectedKey === true)
  check('升级后至少一份升级前备份', dataAfter.backups.length >= 1, dataAfter.backups.join(', '))

  cdp.close()
  app.kill()
  await waitProcessGone(60000)

  // 用与当前 Windows 用户相同的 DPAPI 上下文验证可解密
  const decrypt = await verifyDpapi()
  check('DPAPI 密钥可被当前用户解密', decrypt.ok, decrypt.detail)

  // ---------- 7. 反向测试：篡改安装包 ----------
  console.log('\n[7/7] 反向测试：篡改更新包后必须拒绝安装')
  const tamperedDir = join(updateDir, '..', 'tampered')
  mkdirSync(tamperedDir, { recursive: true })
  const installerName = readdirSync(updateDir).find((name) => name.endsWith('-setup.exe'))
  const tamperedName = `tampered-${installerName}`
  const tamperedBytes = readFileSync(join(updateDir, installerName))
  tamperedBytes[1024] = tamperedBytes[1024] ^ 0xff
  writeFileSync(join(tamperedDir, tamperedName), tamperedBytes)

  const tamperedLatest = JSON.parse(readFileSync(join(updateDir, 'latest.json'), 'utf-8'))
  tamperedLatest.version = '3.3.2-qa.3'
  tamperedLatest.platforms['windows-x86_64'].url = `http://127.0.0.1:${SERVE_PORT}/${encodeURIComponent(tamperedName)}`
  tamperedLatest.platforms['windows-x86_64'].signature = readFileSync(join(updateDir, `${installerName}.sig`), 'utf-8').trim()

  server.close()
  const tamperedServer = createServer((req, res) => {
    const name = decodeURIComponent((req.url ?? '/').replace(/^\//, ''))
    if (name === 'latest.json') {
      res.writeHead(200, { 'content-type': 'application/json' })
      res.end(JSON.stringify(tamperedLatest))
      return
    }
    const file = join(tamperedDir, name)
    if (!existsSync(file)) {
      res.writeHead(404)
      res.end('not found')
      return
    }
    res.writeHead(200, { 'content-type': 'application/octet-stream' })
    res.end(readFileSync(file))
  })
  await new Promise((ok) => tamperedServer.listen(SERVE_PORT, '127.0.0.1', ok))

  app = launchApp()
  cdp = await attachCdp()
  await waitForSelector(cdp, '.side-nav__item')
  await cdp.evaluate(`
    const goSettings = [...document.querySelectorAll('.side-nav__item')].find((b) => b.textContent.includes('设置'))
    goSettings?.click()
    await new Promise((r) => setTimeout(r, 1200))
    const details = [...document.querySelectorAll('details.settings-category')].find((d) => d.textContent.includes('关于应用'))
    details?.setAttribute('open', 'open')
    await new Promise((r) => setTimeout(r, 400))
    return true
  `)
  await cdp.evaluate(`
    [...document.querySelectorAll('.update-card button')].find((b) => b.textContent.includes('检查更新'))?.click()
    await new Promise((r) => setTimeout(r, 3200))
    return true
  `)
  const tamperAvailable = await cdp.evaluate(`
    const group = document.querySelector('[aria-labelledby="settings-update-title"]')
    return group?.querySelector('.settings-state')?.textContent.trim() ?? null
  `)
  check('篡改场景先被识别为新版本（qa.3）', tamperAvailable === '发现新版本', String(tamperAvailable))

  await cdp.evaluate(`
    [...document.querySelectorAll('.update-card button')].find((b) => b.textContent.includes('下载并安装'))?.click()
    await new Promise((r) => setTimeout(r, 6000))
    return true
  `)
  let tamperState = null
  let tamperError = null
  for (let i = 0; i < 20; i += 1) {
    const snapshot = await cdp
      .evaluate(`
        const group = document.querySelector('[aria-labelledby="settings-update-title"]')
        const card = document.querySelector('.update-card')
        return {
          state: group?.querySelector('.settings-state')?.textContent.trim() ?? null,
          error: card?.querySelector('.update-error p')?.textContent.trim() ?? null,
        }
      `)
      .catch(() => null)
    if (snapshot) {
      tamperState = snapshot.state ?? tamperState
      tamperError = snapshot.error ?? tamperError
      if (snapshot.state === '更新失败' && snapshot.error) break
    }
    await sleep(1500)
  }
  check('篡改包被拒绝（状态为更新失败）', tamperState === '更新失败', `${tamperState} / ${tamperError ?? '-'}`)
  check('错误提示说明校验失败', /签名|signature|verify/i.test(String(tamperError ?? '')), String(tamperError ?? '').slice(0, 80))
  const stillAlive = await cdp.evaluate(`
    const group = document.querySelector('[aria-labelledby="settings-update-title"]')
    return { version: group?.querySelector('.update-card__version strong')?.textContent.trim() ?? null, rows: document.querySelectorAll('.side-nav__item').length }
  `)
  check('应用仍可继续使用且版本未变', String(stillAlive.version ?? '').includes('3.3.2-qa.2') && stillAlive.rows >= 4, JSON.stringify(stillAlive))
  await cdp.shot('update-tampered-rejected.png')

  cdp.close()
  app.kill()
  await waitProcessGone(60000)
  tamperedServer.close()

  const failed = results.filter((item) => !item.ok)
  const report = {
    ranAt: new Date().toISOString(),
    oldSetup,
    updateDir,
    identifier: IDENTIFIER,
    installDir: INSTALL_DIR,
    dataDir: DATA_DIR,
    dataBefore: before,
    dataAfter,
    checks: results,
    summary: { total: results.length, passed: results.length - failed.length, failed: failed.length },
  }
  writeFileSync(join(OUT_DIR, 'qa-upgrade-report.json'), JSON.stringify(report, null, 2) + '\n', 'utf-8')
  console.log(`\n${results.length - failed.length}/${results.length} 通过`)
  console.log(`报告：docs/updater/qa-upgrade-report.json`)
  return failed.length === 0 ? 0 : 1
}

async function inspectData() {
  const dbPath = join(DATA_DIR, 'history.sqlite3')
  const script = join(TMP_DIR, 'inspect.py')
  writeFileSync(
    script,
    `import json, os, sqlite3, sys
db = sys.argv[1]
out = {"historyCount": 0, "question": "", "preferences": "", "hasProtectedKey": False, "backups": []}
if os.path.exists(db):
    con = sqlite3.connect(db)
    try:
        out["historyCount"] = con.execute("SELECT COUNT(*) FROM divinations").fetchone()[0]
        row = con.execute("SELECT question FROM divinations ORDER BY id DESC LIMIT 1").fetchone()
        out["question"] = row[0] if row else ""
        pref = con.execute("SELECT value_json FROM app_settings WHERE key='app_preferences'").fetchone()
        out["preferences"] = pref[0] if pref else ""
        key = con.execute("SELECT 1 FROM app_settings WHERE key='deepseek_api_key_protected'").fetchone()
        out["hasProtectedKey"] = key is not None
    finally:
        con.close()
backup_dir = os.path.join(os.path.dirname(db), "backups")
if os.path.isdir(backup_dir):
    out["backups"] = sorted(n for n in os.listdir(backup_dir) if n.startswith("history.pre-update-"))
print(json.dumps(out, ensure_ascii=False))
`,
    'utf-8',
  )
  const output = await new Promise((ok, bad) => {
    const python = process.env.QA_PYTHON ?? 'python'
    const child = spawn(python, [script, dbPath], { stdio: ['ignore', 'pipe', 'ignore'] })
    let buffer = ''
    child.stdout.on('data', (chunk) => {
      buffer += chunk.toString()
    })
    child.on('error', bad)
    child.on('exit', () => ok(buffer.trim()))
  })
  return JSON.parse(output)
}

async function verifyDpapi() {
  const script = join(TMP_DIR, 'dpapi.py')
  writeFileSync(
    script,
    `import json, sqlite3, sys
sys.path.insert(0, sys.argv[1])
from backend.services.ai_secrets import unprotect
db = sqlite3.connect(sys.argv[2])
row = db.execute("SELECT value_json FROM app_settings WHERE key='deepseek_api_key_protected'").fetchone()
import json as _json
db.close()
if not row:
    print(json.dumps({"ok": False, "detail": "未找到受保护密钥"}))
    raise SystemExit(0)
try:
    value = unprotect(_json.loads(row[0]))
    print(json.dumps({"ok": value == "sk-qa-updater-e2e-not-a-real-key", "detail": "decrypted" if value else "empty"}))
except Exception as exc:
    print(json.dumps({"ok": False, "detail": str(exc)[:80]}))
`,
    'utf-8',
  )
  const output = await new Promise((ok, bad) => {
    const python = process.env.QA_PYTHON ?? 'python'
    const child = spawn(python, [script, resolve('.'), join(DATA_DIR, 'history.sqlite3')], {
      stdio: ['ignore', 'pipe', 'ignore'],
    })
    let buffer = ''
    child.stdout.on('data', (chunk) => {
      buffer += chunk.toString()
    })
    child.on('error', bad)
    child.on('exit', () => ok(buffer.trim()))
  })
  try {
    return JSON.parse(output)
  } catch {
    return { ok: false, detail: output.slice(0, 80) }
  }
}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    console.error(`执行失败：${error.message}`)
    process.exit(2)
  })
