#!/usr/bin/env node
// check-links.mjs — 构建产物链接检查（无第三方依赖）
// 用法: node check-links.mjs [--dir <dist路径>] [--external] [--allow <url1,url2,...>] [--base <部署子路径>]
// 退出码: 存在失败 = 1, 否则 0。
import { readFileSync, existsSync, statSync, readdirSync } from 'node:fs';
import { resolve, join, dirname, extname } from 'node:path';

const args = process.argv.slice(2);
const opts = { dir: null, external: false, allow: [], base: null };
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--dir') opts.dir = args[++i];
  else if (a.startsWith('--dir=')) opts.dir = a.slice(6);
  else if (a === '--external') opts.external = true;
  else if (a === '--allow') opts.allow.push(...(args[++i] || '').split(','));
  else if (a.startsWith('--allow=')) opts.allow.push(...a.slice(8).split(','));
  else if (a === '--base') opts.base = args[++i];
  else if (a.startsWith('--base=')) opts.base = a.slice(6);
}
opts.allow = opts.allow.map((s) => s.trim()).filter(Boolean);

function pickDistRoot() {
  const candidates = [join('website', 'dist'), 'dist'];
  for (const c of candidates) if (existsSync(c)) return c;
  return join('website', 'dist');
}
const distRoot = resolve(opts.dir || pickDistRoot());

function walkHtml(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) out.push(...walkHtml(p));
    else if (extname(name).toLowerCase() === '.html') out.push(p);
  }
  return out;
}
function extractUrls(css) {
  const out = [];
  const re = /url\(\s*(['"]?)([^'")]+)\1\s*\)/gi;
  let m;
  while ((m = re.exec(css))) out.push({ kind: 'url()', value: m[2] });
  return out;
}
function extractRefs(html) {
  const refs = [];
  const attrRe = /\b(href|src)\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))/gi;
  let m;
  while ((m = attrRe.exec(html))) refs.push({ kind: m[1], value: m[3] ?? m[4] ?? m[5] ?? '' });
  const blockRe = /<style[^>]*>([\s\S]*?)<\/style>/gi;
  let b;
  while ((b = blockRe.exec(html))) refs.push(...extractUrls(b[1]));
  const attrStyleRe = /style\s*=\s*("([^"]*)"|'([^']*)')/gi;
  let s;
  while ((s = attrStyleRe.exec(html))) refs.push(...extractUrls(s[2] ?? s[3] ?? ''));
  return refs;
}
const isExternal = (u) => /^https?:\/\//i.test(u) || /^\/\//.test(u);
const isSkippable = (u) => /^(#|mailto:|tel:|data:|javascript:|blob:|about:)/i.test(u);
function stripQueryHash(u) { return u.split('#')[0].split('?')[0]; }
function decodeUrl(u) { try { return decodeURIComponent(u); } catch { return u; } }
function realFile(p) {
  if (existsSync(p) && statSync(p).isFile()) return p;
  if (existsSync(p) && statSync(p).isDirectory()) {
    const idx = join(p, 'index.html');
    if (existsSync(idx) && statSync(idx).isFile()) return idx;
  }
  return null;
}
function normalizeBase(b) {
  if (!b || b === '/') return '/';
  let s = b;
  if (!s.startsWith('/')) s = '/' + s;
  if (!s.endsWith('/')) s = s + '/';
  return s;
}
function detectBase(absRefs) {
  // 从含 /assets/ 的绝对引用推断公共前缀（GitHub Pages 子路径 base）
  const cands = absRefs
    .map((r) => {
      const i = r.indexOf('/assets/');
      return i >= 0 ? r.slice(0, i + 1) : null;
    })
    .filter(Boolean);
  if (!cands.length) return '/';
  let common = cands[0];
  for (const c of cands.slice(1)) {
    while (!c.startsWith(common)) {
      common = common.slice(0, -1);
      if (!common) return '/';
    }
  }
  return common.endsWith('/') ? common : common + '/';
}

let base = '/';
function resolveInternal(value, fromFile) {
  let p = stripQueryHash(value).trim();
  p = decodeUrl(p);
  if (!p) return null;
  if (p.startsWith('/')) {
    let rel = p;
    if (base !== '/') {
      const baseNoSlash = base.slice(0, -1);
      if (p === baseNoSlash || p === base) rel = '/';
      else if (p.startsWith(base)) rel = '/' + p.slice(base.length);
      // 其余以 / 开头的路径视为域名根绝对路径，按 dist 根相对回退
    }
    return resolve(distRoot, '.' + rel);
  }
  return resolve(dirname(fromFile), p);
}
function isAllowed(url) {
  return opts.allow.some((e) => {
    if (e.endsWith('*')) return url.startsWith(e.slice(0, -1));
    if (e.startsWith('*')) return url.endsWith(e.slice(1));
    return url === e || url.includes(e);
  });
}

const files = walkHtml(distRoot);
const externalSet = new Set();
const internalRaw = [];
let skipped = 0;
for (const f of files) {
  const html = readFileSync(f, 'utf8');
  for (const { kind, value } of extractRefs(html)) {
    const v = value.trim();
    if (!v) continue;
    if (isSkippable(v)) { skipped++; continue; }
    if (isExternal(v)) { externalSet.add(v.startsWith('//') ? 'https:' + v : v); continue; }
    internalRaw.push({ from: f, ref: v, kind });
  }
}
const absRefs = internalRaw.map((i) => i.ref).filter((r) => r.startsWith('/'));
base = normalizeBase(opts.base || detectBase(absRefs));

const internal = [];
for (const { from, ref, kind } of internalRaw) {
  const resolved = resolveInternal(ref, from);
  if (!resolved) { skipped++; continue; }
  internal.push({ from, ref, resolved, kind });
}
const missing = internal.filter((i) => !realFile(i.resolved));

async function checkExternal(urls) {
  const results = [];
  const CONC = 5;
  let batch = [];
  for (const u of urls) {
    batch.push(run(u));
    if (batch.length >= CONC) { results.push(...(await Promise.all(batch))); batch = []; }
  }
  if (batch.length) results.push(...(await Promise.all(batch)));
  return results;
  async function run(u) {
    if (isAllowed(u)) return { url: u, status: 'allow', code: null, note: '白名单' };
    try {
      const res = await fetch(u, { method: 'HEAD', redirect: 'follow', signal: AbortSignal.timeout(8000) });
      const code = res.status;
      if (code >= 200 && code < 400) return { url: u, status: 'ok', code };
      if ([403, 405, 429].includes(code)) return { url: u, status: 'undecided', code, note: '不可判定' };
      return { url: u, status: 'fail', code };
    } catch {
      return { url: u, status: 'undecided', code: null, note: '不可判定(网络错误)' };
    }
  }
}

const externalList = [...externalSet].sort();
let extResults = [];
if (opts.external && externalList.length) {
  extResults = await checkExternal(externalList);
}
const extFail = extResults.filter((r) => r.status === 'fail');
const totalFail = missing.length + extFail.length;

const lines = [];
lines.push('链接检查 · dist: ' + distRoot + (base !== '/' ? ' · base: ' + base : ''));
lines.push('HTML 文件: ' + files.length + ' 个；内部链接: ' + internal.length + '（缺失 ' + missing.length + '）；外链: ' + externalList.length + ' 个唯一 URL');
if (missing.length) {
  lines.push('--- 缺失的内部链接 ---');
  for (const m of missing) lines.push('  ' + pathRel(m.from) + '  →  ' + m.ref);
}
if (externalList.length) {
  if (!opts.external) {
    lines.push('--- 外链清单（加 --external 检查状态码）---');
    for (const u of externalList) lines.push('  ' + u);
  } else {
    lines.push('--- 外链状态 ---');
    for (const r of extResults) {
      const tag = r.status === 'ok' ? 'OK ' : r.status === 'fail' ? 'FAIL' : r.status === 'allow' ? 'ALLOW' : '?? ';
      lines.push('  [' + tag + (r.code != null ? ' ' + r.code : '') + (r.note ? ' ' + r.note : '') + '] ' + r.url);
    }
  }
}
if (totalFail === 0) {
  lines.push('汇总: ✓ 通过' + (skipped ? '（跳过 ' + skipped + ' 个锚点/协议链接）' : ''));
} else {
  lines.push('汇总: ✗ 存在 ' + totalFail + ' 个失败（内部缺失 ' + missing.length + '，外链失败 ' + extFail.length + '）');
}
console.log(lines.join('\n'));

function pathRel(p) {
  const rel = p.startsWith(distRoot) ? p.slice(distRoot.length).replace(/^[\\/]/, '') : p;
  return rel;
}
process.exitCode = totalFail === 0 ? 0 : 1;
