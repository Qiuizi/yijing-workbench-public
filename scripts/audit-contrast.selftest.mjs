/**
 * audit-contrast.mjs 的反向测试：证明「该失败的会失败」。
 *
 * 覆盖：
 *   1. 合规页面            → exit 0（PASS）
 *   2. 人工低对比度文字     → exit 1（FAIL violations）
 *   3. 渐变/图片背景文字     → exit 3（FAIL unaudited，不当作通过）
 *   4. 页面不可达           → exit 2（FAIL execution）
 *   5. 页面加载但无内容      → exit 2（不得报 0 违规）
 *
 * 用法： node scripts/audit-contrast.selftest.mjs
 * 退出码：0 全部符合预期；1 有不符合预期的用例
 */
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { setTimeout as sleep } from 'node:timers/promises'

const PAGES = {
  '/ok.html': `<!doctype html><html><head><meta charset="utf-8"><style>
    body { margin:0; background:#ffffff; color:#1a1a1a; font:16px/1.6 sans-serif; padding:24px; }
    .muted { color:#5a5a5a; }
  </style></head><body><h1>对比度合规页面</h1><p class="muted">这是一段次要文字，比值高于 4.5。</p></body></html>`,
  '/bad.html': `<!doctype html><html><head><meta charset="utf-8"><style>
    body { margin:0; background:#ffffff; color:#eeeeee; font:16px/1.6 sans-serif; padding:24px; }
  </style></head><body><p>这段文字几乎看不见，必须被判为违规。</p></body></html>`,
  '/gradient.html': `<!doctype html><html><head><meta charset="utf-8"><style>
    body { margin:0; background:#ffffff; font:16px/1.6 sans-serif; padding:24px; }
    .band { background-image: linear-gradient(90deg, #101010, #f0f0f0); padding:24px; color:#ffffff; }
  </style></head><body><div class="band">这段文字压在渐变上，无法准确计算背景。</div></body></html>`,
  '/empty.html': `<!doctype html><html><head><meta charset="utf-8"><title>empty</title></head><body></body></html>`,
}

const server = createServer((req, res) => {
  const body = PAGES[req.url]
  if (!body) {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' })
    res.end('not found')
    return
  }
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
  res.end(body)
})

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
const port = server.address().port
const base = `http://127.0.0.1:${port}`

function runAudit(args, env = {}) {
  return new Promise((resolve) => {
    const child = spawn(
      process.execPath,
      ['scripts/audit-contrast.mjs', ...args],
      { stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, ...env } },
    )
    let out = ''
    child.stdout.on('data', (d) => {
      out += d.toString()
    })
    child.stderr.on('data', (d) => {
      out += d.toString()
    })
    const timer = setTimeout(() => {
      child.kill()
      resolve({ code: 'timeout', out })
    }, 180000)
    child.on('exit', (code) => {
      clearTimeout(timer)
      resolve({ code, out })
    })
  })
}

const cases = [
  {
    name: '合规页面 → 0',
    args: ['--url', `ok=${base}/ok.html@light`, '--min', '4.5'],
    expect: 0,
    check: (out) => out.includes('PASS'),
  },
  {
    name: '低对比度文字 → 1',
    args: ['--url', `bad=${base}/bad.html@light`, '--min', '4.5'],
    expect: 1,
    check: (out) => out.includes('FAIL(violations)') && !out.includes('\nPASS'),
  },
  {
    name: '渐变背景文字 → 3（未评估不算通过）',
    args: ['--url', `grad=${base}/gradient.html@light`, '--min', '4.5'],
    expect: 3,
    check: (out) => out.includes('FAIL(unaudited)'),
  },
  {
    name: '页面不可达 → 2',
    args: ['--url', 'dead=http://127.0.0.1:45999/none.html@light'],
    expect: 2,
    check: (out) => out.includes('FAIL(execution)'),
  },
  {
    name: '页面无内容 → 2（不得报 0 违规）',
    args: ['--url', `empty=${base}/empty.html@light`],
    expect: 2,
    check: (out) => out.includes('FAIL(execution)') && !out.includes('\nPASS'),
  },
]

let failed = 0
console.log(`反向测试基线：${base}\n`)
for (const item of cases) {
  const started = Date.now()
  const { code, out } = await runAudit(item.args, { AUDIT_PORT: '9341' })
  const okCode = code === item.expect
  const okCheck = item.check ? item.check(out) : true
  const ok = okCode && okCheck
  if (!ok) failed += 1
  const ms = Date.now() - started
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${item.name}  exit=${code}（期望 ${item.expect}） ${ms}ms`)
  if (!ok) {
    console.log('----- 输出 -----')
    console.log(out.split('\n').slice(-14).join('\n'))
    console.log('---------------')
  }
  await sleep(300)
}

server.close()
console.log(`\n${cases.length - failed}/${cases.length} 反向用例符合预期`)
process.exit(failed === 0 ? 0 : 1)
