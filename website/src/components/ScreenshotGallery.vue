<script setup lang="ts">
import { ref, nextTick } from 'vue'
import type { Dictionary } from '../i18n/zh'
import { asset } from '../links'

const props = defineProps<{ t: Dictionary }>()

const active = ref(0)
const tablist = ref<HTMLElement | null>(null)
const total = props.t.gallery.screens.length

function shotUrl(id: string): string {
  return asset('shots/' + id + '.png')
}

function select(i: number) {
  active.value = i
}

function focusTab(i: number) {
  nextTick(() => {
    const el = tablist.value?.querySelector('[data-index="' + i + '"]') as HTMLElement | null
    el?.focus()
  })
}

function onKeydown(e: KeyboardEvent) {
  const dir = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
  if (dir === 0) return
  e.preventDefault()
  const next = (active.value + dir + total) % total
  select(next)
  focusTab(next)
}
</script>

<template>
  <section id="screens" class="section section--blend gallery">
    <div class="container">
      <div class="section-head">
        <span class="overline">{{ t.gallery.overline }}</span>
        <h2>{{ t.gallery.title }}</h2>
        <p>{{ t.gallery.subheading }}</p>
      </div>

      <figure id="shot-panel" class="gallery__main" role="tabpanel" :aria-labelledby="'shot-tab-' + active" tabindex="0">
        <div class="gallery__frame">
          <img
            :src="shotUrl(t.gallery.screens[active].id)"
            :alt="t.gallery.screens[active].caption"
            width="1600"
            height="1000"
            loading="lazy"
          />
        </div>
        <figcaption class="gallery__main-cap">
          <span class="gallery__main-cap-index num">{{ String(active + 1).padStart(2, '0') }}<i>/</i>{{ total }}</span>
          <span class="gallery__main-cap-text">
            <strong>{{ t.gallery.screens[active].title }}</strong>
            <span>{{ t.gallery.screens[active].caption }}</span>
          </span>
        </figcaption>
      </figure>

      <div
        ref="tablist"
        class="gallery__tabs"
        role="tablist"
        :aria-label="t.gallery.tablistLabel"
        @keydown="onKeydown"
      >
        <button
          v-for="(s, i) in t.gallery.screens"
          :key="s.id"
          class="gallery__thumb"
          :class="{ 'is-active': i === active }"
          role="tab"
          :id="'shot-tab-' + i"
          :data-index="i"
          :aria-selected="i === active ? 'true' : 'false'"
          :aria-controls="'shot-panel'"
          :tabindex="i === active ? 0 : -1"
          @click="select(i)"
        >
          <span class="gallery__thumb-frame"><img :src="shotUrl(s.id)" alt="" width="160" height="100" loading="lazy" /></span>
          <span class="gallery__thumb-label">{{ s.title }}</span>
        </button>
      </div>
      <p class="gallery__hint">{{ t.gallery.hint }}</p>
    </div>
  </section>
</template>

<style scoped>
.gallery {
  --tone: var(--surface-2);
  --tone-prev: var(--bg);
}

.gallery__main {
  margin: 0;
  position: relative;
  background: var(--surface-1);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 10px;
  box-shadow: var(--shadow-1), var(--sheen);
}
.gallery__frame {
  overflow: hidden;
  border-radius: 4px;
  border: 1px solid var(--line);
  background: var(--surface-3);
}
.gallery__frame img { width: 100%; height: auto; }
/* 夜间压暗亮底截图，避免整屏最亮的是一排界面图 */
:root[data-theme='dark'] .gallery__frame img,
:root[data-theme='dark'] .gallery__thumb-frame img { filter: brightness(.88) saturate(.95); }

.gallery__main-cap {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 14px 6px 4px;
}
.gallery__main-cap-index {
  display: inline-flex;
  align-items: baseline;
  gap: 3px;
  font-family: var(--font-num);
  font-size: var(--t-xs);
  letter-spacing: .08em;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.gallery__main-cap-index i { font-style: normal; opacity: .45; }
.gallery__main-cap-text { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.gallery__main-cap-text strong { font-size: var(--t-sm); color: var(--text-1); letter-spacing: .03em; }
.gallery__main-cap-text span { font-size: var(--t-xs); color: var(--text-2); }

/* 自适应栅格：宽度不够时自动落到 5 / 3 列，不再写死 9 列 */
.gallery__tabs {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(98px, 1fr));
  gap: 10px;
  margin-top: var(--s-5);
}
.gallery__thumb {
  position: relative;
  display: grid;
  gap: 7px;
  padding: 5px 5px 7px;
  background: transparent;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: left;
  transition:
    border-color var(--dur-1) var(--ease-out),
    background-color var(--dur-1) var(--ease-out),
    transform var(--dur-1) var(--ease-out);
}
.gallery__thumb:hover { border-color: var(--line-strong); background: var(--surface-1); transform: translateY(-1px); }
.gallery__thumb.is-active {
  border-color: var(--accent-line);
  background: var(--surface-1);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 12%, transparent);
}
.gallery__thumb-frame { display: block; overflow: hidden; border-radius: 2px; border: 1px solid var(--line); }
.gallery__thumb-frame img { width: 100%; height: auto; display: block; }
.gallery__thumb-label {
  font-family: var(--font-sans);
  font-size: var(--t-micro);
  color: var(--text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gallery__thumb.is-active .gallery__thumb-label { color: var(--accent); }
.gallery__hint { margin: var(--s-3) 0 0; font-size: var(--t-micro); color: var(--text-3); }

@media (max-width: 560px) {
  .gallery__tabs { grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 8px; }
  .gallery__main { padding: 7px; }
}
</style>
