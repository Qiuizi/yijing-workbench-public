<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import type { Dictionary } from '../i18n/zh'
import type { HexagramRecord } from '../data/hexagrams'
import { hexagrams } from '../data/hexagrams'
import { LINKS } from '../links'
import HexagramLines from './HexagramLines.vue'

defineProps<{ t: Dictionary }>()

const group = ref<'all' | 'upper' | 'lower'>('all')
const query = ref('')
const selected = ref<HexagramRecord>(hexagrams[0])
const gridRef = ref<HTMLElement | null>(null)

const filtered = computed<HexagramRecord[]>(() => {
  let list = hexagrams
  if (group.value === 'upper') list = list.filter((h) => h.order <= 30)
  if (group.value === 'lower') list = list.filter((h) => h.order > 30)
  const q = query.value.trim()
  if (q) {
    list = list.filter(
      (h) =>
        String(h.order) === q ||
        h.name.includes(q) ||
        h.title.includes(q) ||
        h.upper.name.includes(q) ||
        h.lower.name.includes(q),
    )
  }
  return list
})

function select(h: HexagramRecord) {
  selected.value = h
}

function focusOrder(order: number) {
  nextTick(() => {
    const el = gridRef.value?.querySelector('[data-order="' + order + '"]') as HTMLElement | null
    el?.focus()
  })
}

function move(dir: number) {
  const list = filtered.value
  if (list.length === 0) return
  let idx = list.findIndex((h) => h.order === selected.value.order)
  if (idx === -1) idx = 0
  const next = list[(idx + dir + list.length) % list.length]
  select(next)
  focusOrder(next.order)
}

function onGridKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); move(1) }
  else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); move(-1) }
  else if (e.key === 'Home') { e.preventDefault(); if (filtered.value[0]) { select(filtered.value[0]); focusOrder(filtered.value[0].order) } }
  else if (e.key === 'End') { e.preventDefault(); const l = filtered.value; if (l[l.length - 1]) { select(l[l.length - 1]); focusOrder(l[l.length - 1].order) } }
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}
</script>

<template>
  <section id="hexagrams" class="section paper paper-noise">
    <div class="container">
      <div class="section-head">
        <span class="overline">{{ t.atlas.overline }}</span>
        <h2>{{ t.atlas.title }}</h2>
        <p>{{ t.atlas.subheading }}</p>
      </div>

      <div class="atlas__controls">
        <label class="atlas__search">
          <span class="sr-only">{{ t.atlas.searchPlaceholder }}</span>
          <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><circle cx="7" cy="7" r="5"/><line x1="11" y1="11" x2="15" y2="15"/></svg>
          <input v-model="query" type="search" :placeholder="t.atlas.searchPlaceholder" />
        </label>

        <div class="atlas__groups" role="group" :aria-label="t.atlas.count">
          <button type="button" :aria-pressed="group === 'all' ? 'true' : 'false'" @click="group = 'all'">{{ t.atlas.groupAll }}</button>
          <button type="button" :aria-pressed="group === 'upper' ? 'true' : 'false'" @click="group = 'upper'">{{ t.atlas.groupUpper }}</button>
          <button type="button" :aria-pressed="group === 'lower' ? 'true' : 'false'" @click="group = 'lower'">{{ t.atlas.groupLower }}</button>
        </div>
      </div>

      <div class="atlas__layout">
        <div ref="gridRef" class="atlas__grid" @keydown="onGridKeydown">
          <button
            v-for="h in filtered"
            :key="h.order"
            type="button"
            class="cell"
            :class="{ 'is-selected': h.order === selected.order }"
            :data-order="h.order"
            :aria-pressed="h.order === selected.order ? 'true' : 'false'"
            :aria-label="pad(h.order) + ' ' + h.title"
            :tabindex="h.order === selected.order ? 0 : -1"
            @click="select(h)"
          >
            <span class="cell__order">{{ pad(h.order) }}</span>
            <span class="cell__lines"><HexagramLines :binary="h.binary" size="sm" /></span>
            <span class="cell__name">{{ h.name }}</span>
          </button>
          <p v-if="filtered.length === 0" class="atlas__empty">{{ t.atlas.noResult }}</p>
        </div>

        <div class="atlas__detail" role="region" :aria-label="t.atlas.regionLabel" aria-live="polite">
          <div class="detail__head">
            <span class="detail__num">{{ pad(selected.order) }}</span>
            <h3>{{ selected.title }}</h3>
          </div>
          <div class="detail__lines"><HexagramLines :binary="selected.binary" size="lg" /></div>

          <dl class="detail__trigrams">
            <div>
              <dt>{{ t.atlas.upperLabel }}</dt>
              <dd>{{ selected.upper.symbol }} {{ selected.upper.name }} · {{ selected.upper.image }}</dd>
            </div>
            <div>
              <dt>{{ t.atlas.lowerLabel }}</dt>
              <dd>{{ selected.lower.symbol }} {{ selected.lower.name }} · {{ selected.lower.image }}</dd>
            </div>
          </dl>

          <h4 class="detail__judgment-label">{{ t.atlas.judgmentLabel }}</h4>
          <p class="detail__judgment">{{ selected.judgment }}</p>

          <p class="detail__source">
            {{ t.atlas.sourceLabel }}
            <a :href="LINKS.source" target="_blank" rel="noopener">{{ t.atlas.sourceText }}</a>
          </p>

          <p class="detail__status">
            <span>{{ t.atlas.statusLabel }}</span>{{ t.atlas.statusText }}
          </p>
          <p class="detail__hint">{{ t.atlas.selectHint }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.atlas__controls { display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between; margin-bottom: var(--s-5); }

.atlas__search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  min-width: 260px;
  border: 1px solid rgba(43, 51, 46, .3);
  border-radius: var(--radius-sm);
  background: var(--paper-bright);
  color: var(--ink-text-muted);
  flex: 1 1 280px;
  max-width: 420px;
}
.atlas__search input {
  flex: 1;
  border: 0;
  outline: none;
  background: transparent;
  font-family: var(--font-serif);
  font-size: 14px;
  color: var(--ink-text);
}
.atlas__search:focus-within { border-color: var(--gold-500); }

.atlas__groups { display: inline-flex; border: 1px solid rgba(43, 51, 46, .3); border-radius: var(--radius-sm); overflow: hidden; }
.atlas__groups button {
  padding: 9px 16px;
  border: 0;
  border-right: 1px solid rgba(43, 51, 46, .25);
  background: transparent;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--ink-text-soft);
  cursor: pointer;
  transition: background-color .18s ease, color .18s ease;
}
.atlas__groups button:last-child { border-right: 0; }
.atlas__groups button:hover { background: rgba(43, 51, 46, .05); }
.atlas__groups button[aria-pressed='true'] { background: var(--ink-text); color: var(--paper-bright); }

.atlas__layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: var(--s-6); align-items: start; }

.atlas__grid {
  display: grid;
  /* 64 卦在桌面端按 8 栏排布，正好 8×8，不留孤行。 */
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 8px;
}
.cell {
  display: grid;
  gap: 6px;
  justify-items: center;
  padding: 12px 8px 10px;
  background: var(--paper-bright);
  border: 1px solid rgba(43, 51, 46, .2);
  border-radius: 3px;
  cursor: pointer;
  color: var(--ink-text);
  transition: border-color .16s ease, background-color .16s ease, box-shadow .16s ease;
}
.cell:hover { border-color: var(--gold-500); }
.cell.is-selected { border-color: var(--cinnabar); background: #fbf6f0; box-shadow: inset 0 0 0 1px var(--cinnabar); }
.cell__order { font-family: var(--font-num); font-size: 10px; letter-spacing: .14em; color: var(--ink-text-muted); }
.cell__lines { width: 44%; color: var(--ink-text); }
.cell.is-selected .cell__lines { color: var(--cinnabar); }
.cell__name { font-size: 15px; font-weight: 600; letter-spacing: .04em; }
.atlas__empty { grid-column: 1 / -1; padding: var(--s-7) 0; text-align: center; color: var(--ink-text-muted); }

.atlas__detail {
  position: sticky;
  top: 96px;
  padding: var(--s-5);
  background: var(--paper-bright);
  border: 1px solid rgba(201, 162, 39, .5);
  border-radius: 4px;
  box-shadow: 0 20px 50px rgba(43, 51, 46, .06);
}
.detail__head { display: flex; align-items: baseline; gap: 12px; }
.detail__num { font-family: var(--font-num); font-size: 30px; line-height: 1; color: var(--cinnabar); }
.detail__head h3 { font-size: 21px; letter-spacing: .04em; color: var(--ink-text); }
.detail__lines { width: 96px; margin: var(--s-5) auto var(--s-5); color: var(--ink-text); }

.detail__trigrams { margin: 0 0 var(--s-4); display: grid; gap: 8px; }
.detail__trigrams div { display: flex; gap: 12px; font-size: 14px; }
.detail__trigrams dt { flex: 0 0 auto; color: var(--ink-text-muted); }
.detail__trigrams dd { margin: 0; color: var(--ink-text); }

.detail__judgment-label { font-size: 12px; font-family: var(--font-sans); font-weight: 600; letter-spacing: .12em; color: var(--gold-600); margin-bottom: var(--s-2); }
.detail__judgment { margin: 0; font-size: 16px; line-height: 1.9; color: var(--ink-text); white-space: pre-wrap; }

.detail__source { margin: var(--s-4) 0 0; font-size: 12.5px; color: var(--ink-text-muted); }
.detail__source a { color: var(--cinnabar); border-bottom: 1px solid rgba(169, 71, 54, .4); }
.detail__source a:hover { border-bottom-color: var(--cinnabar); }

.detail__status { margin: var(--s-3) 0 0; padding: 10px 12px; font-size: 12px; line-height: 1.7; color: var(--ink-text-soft); background: rgba(201, 162, 39, .12); border-left: 2px solid var(--gold-500); }
.detail__status span { font-weight: 600; }
.detail__hint { margin: var(--s-4) 0 0; font-size: 11.5px; color: var(--ink-text-muted); }

@media (max-width: 900px) {
  .atlas__layout { grid-template-columns: 1fr; }
  .atlas__detail { position: static; }
}
@media (max-width: 700px) {
  .atlas__grid { grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 6px; }
}
@media (max-width: 480px) {
  .atlas__grid { grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 6px; }
  .cell { padding: 10px 5px 8px; }
  .cell__name { font-size: 14px; }
}
</style>
