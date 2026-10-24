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

async function copySha() {
  try {
    await navigator.clipboard.writeText(release.value.sha256)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
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
onBeforeUnmount(() => ctrl?.abort())

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
  <section id="download" class="section shell grain-dark">
    <div class="container">
      <div class="section-head">
        <span class="overline">{{ t.download.overline }}</span>
        <h2>{{ t.download.title }}</h2>
        <p>{{ t.download.subheading }}</p>
      </div>

      <div class="dl-card">
        <div class="dl-card__head">
          <div>
            <span class="dl-card__label">{{ t.download.versionLabel }}</span>
            <span class="dl-card__tag">{{ release.tag }}</span>
          </div>
          <div>
            <span class="dl-card__label">{{ t.download.publishedLabel }}</span>
            <span class="dl-card__tag">{{ release.date }}</span>
          </div>
          <p v-if="status === 'loading'" class="dl-card__status" role="status">{{ t.download.loading }}</p>
          <p v-else-if="status === 'fallback'" class="dl-card__status" role="status">{{ t.download.fallbackNote }}</p>
        </div>

        <div class="dl-card__asset">
          <div class="dl-card__asset-meta">
            <span class="dl-card__label">{{ t.download.assetLabel }}</span>
            <strong class="dl-card__asset-name">{{ release.exe.name }}</strong>
            <span class="dl-card__asset-size">{{ sizeMiB }} · {{ sizeBytes }}</span>
          </div>
          <a class="btn btn--primary" :href="release.exe.url">{{ t.download.downloadBtn }}</a>
        </div>

        <div class="dl-card__sha">
          <span class="dl-card__label">{{ t.download.shaLabel }}</span>
          <code class="dl-card__sha-value">{{ shaGroups }}</code>
          <button class="dl-card__copy" type="button" @click="copySha">{{ copied ? t.download.copied : t.download.copy }}</button>
          <a class="dl-card__link" :href="release.sumsUrl">{{ t.download.checksumsBtn }}</a>
        </div>

        <div class="dl-card__links">
          <a class="dl-card__link" :href="release.provenanceUrl">{{ t.download.provenanceBtn }}</a>
          <span aria-hidden="true">·</span>
          <a class="dl-card__link" :href="LINKS.releases">{{ t.download.historyLink }}</a>
          <span aria-hidden="true">·</span>
          <a class="dl-card__link" :href="release.htmlUrl">Release {{ release.tag }}</a>
        </div>

        <div class="dl-card__notes">
          <div class="note">
            <strong>{{ t.download.unsignedTitle }}</strong>
            <p>{{ t.download.unsignedNote }}</p>
          </div>
          <div class="note">
            <strong>{{ t.download.webviewTitle }}</strong>
            <p>{{ t.download.webviewNote }}</p>
          </div>
          <div class="note">
            <strong>{{ t.download.installNote }}</strong>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.dl-card {
  max-width: 880px;
  border: 1px solid rgba(214, 185, 121, .4);
  border-radius: 4px;
  background: linear-gradient(180deg, rgba(29, 43, 39, .6), rgba(20, 32, 29, .4));
  overflow: hidden;
}
.dl-card__head { display: flex; flex-wrap: wrap; gap: 32px; align-items: baseline; padding: var(--s-5) var(--s-5) var(--s-4); border-bottom: 1px solid rgba(214, 185, 121, .18); }
.dl-card__head > div { display: flex; gap: 10px; align-items: baseline; }
.dl-card__label { font-family: var(--font-sans); font-size: 11px; letter-spacing: .18em; text-transform: uppercase; color: var(--gold-300); }
.dl-card__tag { font-family: var(--font-num); font-size: 18px; color: var(--shell-text); letter-spacing: .03em; }
.dl-card__status { margin: 0; margin-left: auto; font-size: 12.5px; color: var(--gold-300); }

.dl-card__asset { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: var(--s-5); border-bottom: 1px solid rgba(214, 185, 121, .18); flex-wrap: wrap; }
.dl-card__asset-meta { display: grid; gap: 4px; }
.dl-card__asset-name { font-size: 15px; color: var(--shell-text); word-break: break-all; }
.dl-card__asset-size { font-family: var(--font-sans); font-size: 12.5px; color: var(--shell-text-soft); }

.dl-card__sha { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; padding: var(--s-4) var(--s-5); border-bottom: 1px solid rgba(214, 185, 121, .18); }
.dl-card__sha-value {
  font-family: var(--font-num);
  font-size: 13px;
  color: var(--shell-text);
  letter-spacing: .03em;
  font-variant-numeric: tabular-nums;
  background: rgba(13, 22, 20, .7);
  padding: 8px 12px;
  border-radius: 3px;
  border: 1px solid rgba(214, 185, 121, .22);
  user-select: all;
  word-break: break-all;
}
.dl-card__copy {
  padding: 7px 12px;
  border: 1px solid rgba(214, 185, 121, .4);
  border-radius: 3px;
  background: transparent;
  color: var(--gold-300);
  font-family: var(--font-sans);
  font-size: 12px;
  cursor: pointer;
  transition: background-color .18s ease, border-color .18s ease;
}
.dl-card__copy:hover { background: rgba(214, 185, 121, .1); border-color: var(--gold-300); }

.dl-card__links { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: var(--s-4) var(--s-5); border-bottom: 1px solid rgba(214, 185, 121, .18); color: var(--shell-text-soft); }
.dl-card__link { color: var(--gold-300); font-size: 13px; border-bottom: 1px solid rgba(201, 162, 39, .35); transition: border-color .18s ease, color .18s ease; }
.dl-card__link:hover { color: var(--gold-400); border-bottom-color: var(--gold-400); }

.dl-card__notes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: rgba(214, 185, 121, .14); }
.note { padding: var(--s-4) var(--s-5); background: var(--ink-900); }
.note strong { display: block; font-size: 13px; color: var(--gold-300); letter-spacing: .04em; margin-bottom: 6px; }
.note p { margin: 0; font-size: 12.5px; line-height: 1.7; color: var(--shell-text-soft); }

@media (max-width: 760px) {
  .dl-card__notes { grid-template-columns: 1fr; }
  .dl-card__head { gap: 16px; }
  .dl-card__status { margin-left: 0; flex-basis: 100%; }
}
</style>
