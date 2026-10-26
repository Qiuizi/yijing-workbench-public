<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import type { Dictionary } from '../i18n/zh'
import { GITHUB_API, LINKS, RELEASE_STATIC } from '../links'

defineProps<{ t: Dictionary }>()

interface ExeAsset { name: string; size: number; url: string }
interface ReleaseInfo { tag: string; date: string; exe: ExeAsset; sumsUrl: string; provenanceUrl: string; htmlUrl: string; sha256: string }

const status = ref<'loading' | 'loaded' | 'fallback'>('loading')
const release = ref<ReleaseInfo>({
  tag: RELEASE_STATIC.tag,
  date: RELEASE_STATIC.date,
  exe: { name: RELEASE_STATIC.assetName, size: RELEASE_STATIC.bytes, url: LINKS.download },
  sumsUrl: LINKS.checksums,
  provenanceUrl: LINKS.provenance,
  htmlUrl: LINKS.releaseTag,
  sha256: RELEASE_STATIC.sha256,
})

let ctrl: AbortController | null = null

const copied = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | null = null

async function copySha() {
  try {
    await navigator.clipboard.writeText(release.value.sha256)
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // silent: clipboard unavailable
  }
}

function fallbackRelease(): ReleaseInfo {
  return {
    tag: RELEASE_STATIC.tag,
    date: RELEASE_STATIC.date,
    exe: { name: RELEASE_STATIC.assetName, size: RELEASE_STATIC.bytes, url: LINKS.download },
    sumsUrl: LINKS.checksums,
    provenanceUrl: LINKS.provenance,
    htmlUrl: LINKS.releaseTag,
    sha256: RELEASE_STATIC.sha256,
  }
}

async function load() {
  ctrl = new AbortController()
  const timer = setTimeout(() => ctrl?.abort(), 6000)
  try {
    const res = await fetch(GITHUB_API, {
      signal: ctrl.signal,
      headers: { Accept: 'application/vnd.github+json' },
    })
    if (!res.ok) throw new Error('bad status ' + res.status)
    const data = await res.json()
    // The EXE, version, checksums link and SHA-256 must belong to the SAME release.
    const tag = String(data?.tag_name ?? '')
    if (!/^v\d+\.\d+\.\d+$/.test(tag) || !Array.isArray(data.assets)) {
      throw new Error('invalid release response')
    }
    const name = `yijing-workbench-${tag.slice(1)}-x64-setup.exe`
    const exe = data.assets.find((asset: { name?: string }) => asset.name === name)
    const sums = data.assets.find((asset: { name?: string }) => asset.name === 'SHA256SUMS.txt')
    const provenance = data.assets.find((asset: { name?: string }) => asset.name === 'PROVENANCE.md')
    const sha256 = String(exe?.digest ?? '').match(/^sha256:([0-9a-f]{64})$/i)?.[1]?.toUpperCase()
    const prefix = `https://github.com/Qiuizi/yijing-workbench-public/releases/download/${tag}/`
    if (!exe || !sums || !provenance || !sha256 ||
        !Number.isSafeInteger(exe.size) || exe.size <= 0 ||
        exe.browser_download_url !== prefix + name ||
        sums.browser_download_url !== prefix + 'SHA256SUMS.txt' ||
        provenance.browser_download_url !== prefix + 'PROVENANCE.md') {
      throw new Error('unverified release metadata')
    }
    release.value = {
      tag,
      date: String(data.published_at ?? RELEASE_STATIC.date).slice(0, 10),
      exe: { name, size: exe.size, url: exe.browser_download_url },
      sumsUrl: sums.browser_download_url,
      provenanceUrl: provenance.browser_download_url,
      htmlUrl: `https://github.com/Qiuizi/yijing-workbench-public/releases/tag/${tag}`,
      sha256,
    }
    status.value = 'loaded'
  } catch {
    release.value = fallbackRelease()
    status.value = 'fallback'
  } finally {
    clearTimeout(timer)
  }
}

onMounted(load)
onBeforeUnmount(() => {
  ctrl?.abort()
  if (copyTimer) clearTimeout(copyTimer)
})

const sizeMiB = computed(() => (release.value.exe.size / 1048576).toFixed(1) + ' MiB')
const sizeBytes = computed(() => release.value.exe.size.toLocaleString('en-US') + ' bytes')

const shaGroups = computed(() => {
  const s = release.value.sha256
  const parts: string[] = []
  for (let i = 0; i < s.length; i += 8) parts.push(s.slice(i, i + 8))
  return parts.join(' ')
})
</script>

<template>
  <section id="download" class="section section--blend download">
    <div class="container">
      <div class="section-head">
        <span class="overline">{{ t.download.overline }}</span>
        <h2>{{ t.download.title }}</h2>
        <p>{{ t.download.subheading }}</p>
      </div>

      <div class="dl-slab">
        <div class="dl-slab__head">
          <div class="dl-pair">
            <span class="dl-label">{{ t.download.versionLabel }}</span>
            <span class="dl-value num">{{ release.tag }}</span>
          </div>
          <div class="dl-pair">
            <span class="dl-label">{{ t.download.publishedLabel }}</span>
            <span class="dl-value num">{{ release.date }}</span>
          </div>
          <p v-if="status === 'loading'" class="dl-status" role="status">
            <span class="dl-status__dot" aria-hidden="true"></span>{{ t.download.loading }}
          </p>
          <p v-else-if="status === 'fallback'" class="dl-status" role="status">
            <span class="dl-status__dot" aria-hidden="true"></span>{{ t.download.fallbackNote }}
          </p>
        </div>

        <div class="dl-slab__asset">
          <div class="dl-asset-meta">
            <span class="dl-label">{{ t.download.assetLabel }}</span>
            <strong class="dl-asset-name">{{ release.exe.name }}</strong>
            <span class="dl-asset-size num">{{ sizeMiB }} · {{ sizeBytes }}</span>
          </div>
          <a class="btn btn--primary" :href="release.exe.url">{{ t.download.downloadBtn }}</a>
        </div>

        <div class="dl-slab__sha">
          <span class="dl-label">{{ t.download.shaLabel }}</span>
          <code class="dl-sha">{{ shaGroups }}</code>
          <button
            class="dl-copy"
            :class="{ 'is-copied': copied }"
            type="button"
            :aria-label="t.download.copy"
            @click="copySha"
          >
            <svg v-if="!copied" viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.4"/><path d="M10.5 5.5v-1a1.4 1.4 0 0 0-1.4-1.4H3.9a1.4 1.4 0 0 0-1.4 1.4v5.2a1.4 1.4 0 0 0 1.4 1.4h1"/></svg>
            <svg v-else viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3.4 8.4 3 3 6.2-6.6"/></svg>
            <span>{{ copied ? t.download.copied : t.download.copy }}</span>
          </button>
          <a class="dl-link" :href="release.sumsUrl">{{ t.download.checksumsBtn }}</a>
        </div>

        <div class="dl-slab__links">
          <a class="dl-link" :href="release.provenanceUrl">{{ t.download.provenanceBtn }}</a>
          <a class="dl-link" :href="LINKS.releases">{{ t.download.historyLink }}</a>
          <a class="dl-link" :href="release.htmlUrl">Release {{ release.tag }}</a>
        </div>

        <div class="dl-slab__notes">
          <div class="dl-note">
            <strong>{{ t.download.unsignedTitle }}</strong>
            <p>{{ t.download.unsignedNote }}</p>
          </div>
          <div class="dl-note">
            <strong>{{ t.download.webviewTitle }}</strong>
            <p>{{ t.download.webviewNote }}</p>
          </div>
          <div class="dl-note">
            <strong>{{ t.download.installNote }}</strong>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.download {
  --tone: var(--bg);
  --tone-prev: var(--surface-2);
}

/* 全站唯一的墨玉块：把语义色在局部重挂一遍，内部组件无需知道自己在暗底上 */
.dl-slab {
  --text-1: var(--shell-text);
  --text-2: var(--shell-text-soft);
  --text-3: #98a093;
  --line: rgba(211, 181, 124, .18);
  --line-strong: rgba(211, 181, 124, .3);
  --accent: #c4785f;
  --accent-strong: #d18d75;
  --accent-soft: rgba(196, 120, 95, .14);
  --accent-line: rgba(196, 120, 95, .36);
  --bronze: var(--shell-bronze);
  --text-inverse: var(--c-night-900);

  position: relative;
  overflow: hidden;
  padding: clamp(20px, 2.6vw, 30px);
  border-radius: var(--radius-lg);
  /* 底色只走 background-color：装饰性渐变放 ::before，
     这样「有效背景」可被审计工具精确计算，高对比模式下也不会塌。 */
  background-color: var(--shell-bg);
  border: 1px solid rgba(211, 181, 124, .16);
  box-shadow:
    inset 0 1px 0 rgba(233, 228, 214, .07),
    0 34px 70px -48px rgba(15, 23, 19, .7);
  color: var(--text-1);
}
/* 夜间把它抬到页面底色之上，避免变成一块更黑的洞 */
:root[data-theme='dark'] .dl-slab {
  --shell-bg: var(--c-night-850);
  --shell-bg-2: var(--c-night-800);
  border-color: rgba(211, 181, 124, .22);
}

/* 暖光与内高光都是装饰层：不参与文字背景计算 */
.dl-slab::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background-image:
    radial-gradient(90% 120% at 8% 0%, rgba(211, 181, 124, .08), transparent 58%),
    linear-gradient(180deg, rgba(28, 39, 33, .55), transparent 72%);
  box-shadow: inset 0 0 0 1px rgba(233, 228, 214, .03);
}

.dl-slab__head {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 34px;
  align-items: baseline;
  padding-bottom: var(--s-4);
}
.dl-pair { display: flex; gap: 9px; align-items: baseline; }
.dl-label {
  font-family: var(--font-sans);
  font-size: var(--t-micro);
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--bronze);
}
.dl-value {
  font-family: var(--font-num);
  font-size: 17px;
  letter-spacing: .02em;
  font-variant-numeric: tabular-nums;
  color: var(--text-1);
}
.dl-status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin: 0 0 0 auto;
  font-size: var(--t-micro);
  color: var(--text-2);
}
.dl-status__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--bronze);
  animation: breathe 2.4s var(--ease-soft) infinite;
}
@keyframes breathe {
  0%, 100% { opacity: .35; }
  50% { opacity: 1; }
}

.dl-slab__asset {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  padding: var(--s-5) 0;
  border-top: 1px solid var(--line);
}
.dl-asset-meta { display: grid; gap: 5px; min-width: 0; }
.dl-asset-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1);
  word-break: break-all;
  letter-spacing: .01em;
}
.dl-asset-size {
  font-family: var(--font-sans);
  font-size: var(--t-micro);
  font-variant-numeric: tabular-nums;
  color: var(--text-2);
}

.dl-slab__sha {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: var(--s-4) 0;
  border-top: 1px solid var(--line);
}
.dl-sha {
  font-family: 'Consolas', 'SFMono-Regular', ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.6;
  letter-spacing: .02em;
  font-variant-numeric: tabular-nums;
  color: var(--text-1);
  background: rgba(9, 15, 12, .5);
  padding: 7px 11px;
  border-radius: var(--radius-xs);
  border: 1px solid var(--line);
  user-select: all;
  word-break: break-all;
}
.dl-copy {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 78px;
  padding: 7px 11px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--bronze);
  font-family: var(--font-sans);
  font-size: var(--t-micro);
  cursor: pointer;
  transition: background-color var(--dur-1) var(--ease-out), border-color var(--dur-1) var(--ease-out), color var(--dur-1) var(--ease-out);
}
.dl-copy:hover { background: rgba(211, 181, 124, .1); border-color: var(--bronze); }
.dl-copy.is-copied { color: var(--c-jade-400); border-color: rgba(127, 164, 139, .5); animation: seal-pop .34s var(--ease-out); }

.dl-slab__links {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  padding: var(--s-4) 0;
  border-top: 1px solid var(--line);
  color: var(--text-2);
}
.dl-link {
  color: var(--bronze);
  font-size: var(--t-xs);
  border-bottom: 1px solid rgba(211, 181, 124, .28);
  transition: border-color var(--dur-1) var(--ease-out), color var(--dur-1) var(--ease-out);
}
.dl-link:hover { color: var(--shell-text); border-bottom-color: var(--shell-text); }

/* 三栏说明：用 1px 的低对比竖线咬合，而不是把每块都框起来 */
.dl-slab__notes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
  gap: 1px;
  margin-top: var(--s-2);
  background: var(--line);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.dl-note {
  padding: var(--s-4) var(--s-4) var(--s-4) 0;
  padding-inline: 0 var(--s-4);
  background: var(--shell-bg);
}
.dl-note:first-child { padding-left: var(--s-4); }
.dl-note strong {
  display: block;
  margin-bottom: 5px;
  font-size: var(--t-micro);
  font-weight: 600;
  letter-spacing: .04em;
  color: var(--bronze);
}
.dl-note p {
  margin: 0;
  font-size: var(--t-micro);
  line-height: 1.75;
  color: var(--text-2);
}

@media (max-width: 760px) {
  .dl-status { margin-left: 0; flex-basis: 100%; }
  .dl-slab__sha { gap: 8px; }
  .dl-note, .dl-note:first-child { padding-inline: 0; }
  .dl-note { padding-block: var(--s-3); }
}
</style>
