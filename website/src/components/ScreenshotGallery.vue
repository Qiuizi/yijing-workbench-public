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
  <section id="screens" class="section paper paper-noise">
    <div class="container">
      <div class="section-head">
        <span class="overline">{{ t.gallery.overline }}</span>
        <h2>{{ t.gallery.title }}</h2>
        <p>{{ t.gallery.subheading }}</p>
      </div>

      <div class="gallery__ornament-row" aria-hidden="true">
        <img :src="asset('brand/ornament-yao.svg')" alt="" width="220" height="14" />
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
          <span class="gallery__main-cap-index">{{ active + 1 }} / {{ total }}</span>
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
        aria-label="Screenshots"
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
          <img :src="shotUrl(s.id)" alt="" width="160" height="100" loading="lazy" />
          <span class="gallery__thumb-label">{{ s.title }}</span>
        </button>
      </div>
      <p class="gallery__hint">{{ t.gallery.hint }}</p>
    </div>
  </section>
</template>

<style scoped>
.gallery__ornament-row { display: flex; justify-content: center; margin-bottom: var(--s-4); color: var(--gold-500); }
.gallery__ornament-row img { opacity: .7; }
.gallery__main {
  margin: 0;
  position: relative;
  background: linear-gradient(180deg, rgba(214,185,121,.12), rgba(214,185,121,.03));
  border: 1px solid rgba(201, 162, 39, .5);
  border-radius: 4px;
  padding: 10px;
}
.gallery__frame {
  overflow: hidden;
  border-radius: 2px;
  border: 1px solid rgba(43, 51, 46, .35);
}
.gallery__frame img {
  width: calc(100% + 12px);
  max-width: none;
  height: auto;
  margin-right: -12px;
}
.gallery__main-cap {
  display: flex;
  align-items: baseline;
  gap: 16px;
  padding: 14px 6px 4px;
}
.gallery__main-cap-index {
  font-family: var(--font-num);
  font-size: 13px;
  letter-spacing: .12em;
  color: var(--cinnabar);
}
.gallery__main-cap-text { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.gallery__main-cap-text strong { font-size: 15px; color: var(--ink-text); }
.gallery__main-cap-text span { font-size: 13px; color: var(--ink-text-soft); }

.gallery__tabs {
  display: grid;
  grid-template-columns: repeat(9, 1fr);
  gap: 10px;
  margin-top: var(--s-5);
}
.gallery__thumb {
  display: grid;
  gap: 6px;
  padding: 5px;
  background: transparent;
  border: 1px solid rgba(43, 51, 46, .22);
  border-radius: 3px;
  cursor: pointer;
  text-align: left;
  transition: border-color .18s ease, background-color .18s ease, transform .18s ease;
}
.gallery__thumb:hover { border-color: var(--gold-500); }
.gallery__thumb.is-active { border-color: var(--cinnabar); background: rgba(169, 71, 54, .05); }
.gallery__thumb img { width: 100%; height: auto; border-radius: 2px; }
.gallery__thumb-label {
  font-family: var(--font-sans);
  font-size: 10.5px;
  color: var(--ink-text-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.gallery__hint { margin: var(--s-3) 0 0; font-size: 12px; color: var(--ink-text-muted); }

@media (max-width: 900px) {
  .gallery__tabs { grid-template-columns: repeat(5, 1fr); }
}
@media (max-width: 560px) {
  .gallery__tabs { grid-template-columns: repeat(3, 1fr); }
}
</style>
