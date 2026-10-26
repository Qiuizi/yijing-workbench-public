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
  <section id="hexagrams" class="section section--blend atlas">
    <div class="container">
      <div class="section-head">
        <span class="overline">{{ t.atlas.overline }}</span>
        <h2>{{ t.atlas.title }}</h2>
        <p>{{ t.atlas.subheading }}</p>
      </div>

      <div class="atlas__controls">
        <label class="atlas__search ink-field">
          <span class="sr-only">{{ t.atlas.searchPlaceholder }}</span>
          <svg class="atlas__search-icon" viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" aria-hidden="true"><circle cx="7" cy="7" r="4.6"/><line x1="10.6" y1="10.6" x2="14" y2="14"/></svg>
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
            <span class="cell__order num">{{ pad(h.order) }}</span>
            <span class="cell__lines"><HexagramLines :binary="h.binary" size="sm" /></span>
            <span class="cell__name">{{ h.name }}</span>
          </button>
          <p v-if="filtered.length === 0" class="atlas__empty">{{ t.atlas.noResult }}</p>
        </div>

        <div class="atlas__detail" role="region" :aria-label="t.atlas.regionLabel" aria-live="polite">
          <div class="detail__head">
            <span class="detail__num num">{{ pad(selected.order) }}</span>
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
.atlas {
  --tone: var(--surface-2);
  --tone-prev: var(--bg);
}

.atlas__controls {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--s-5);
}

.atlas__search {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 13px;
  min-width: 240px;
  flex: 1 1 260px;
  max-width: 380px;
  border: 1px solid var(--line-strong);
  background: var(--surface-1);
  color: var(--text-3);
  transition: border-color var(--dur-1) var(--ease-out), background-color var(--dur-1) var(--ease-out);
}
.atlas__search:focus-within { border-color: var(--accent-line); color: var(--accent); }
.atlas__search-icon { flex: 0 0 auto; }
.atlas__search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  font-family: var(--font-serif);
  font-size: var(--t-sm);
  color: var(--text-1);
}

/* 分段控件：轨道用二级表面，选中项用一级表面浮起，不画粗边 */
.atlas__groups {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
}
.atlas__groups button {
  padding: 7px 14px;
  border: 0;
  border-radius: 3px;
  background: transparent;
  font-family: var(--font-sans);
  font-size: var(--t-xs);
  color: var(--text-2);
  cursor: pointer;
  transition: background-color var(--dur-1) var(--ease-out), color var(--dur-1) var(--ease-out), box-shadow var(--dur-1) var(--ease-out);
}
.atlas__groups button:hover { color: var(--text-1); background: var(--surface-2); }
.atlas__groups button[aria-pressed='true'] {
  background: var(--surface-1);
  color: var(--accent);
  font-weight: 600;
  box-shadow: 0 1px 2px color-mix(in srgb, var(--text-1) 8%, transparent), inset 0 0 0 1px var(--accent-line);
}

.atlas__layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 316px;
  gap: clamp(18px, 2.4vw, 28px);
  align-items: start;
}

.atlas__grid {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 7px;
}
.cell {
  display: grid;
  gap: 5px;
  justify-items: center;
  padding: 11px 6px 9px;
  background: color-mix(in srgb, var(--surface-1) 62%, transparent);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-1);
  transition:
    border-color var(--dur-1) var(--ease-out),
    background-color var(--dur-1) var(--ease-out),
    box-shadow var(--dur-1) var(--ease-out);
}
.cell:hover { background: var(--surface-1); border-color: var(--line-strong); }
.cell.is-selected {
  background: var(--accent-soft);
  border-color: var(--accent-line);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 12%, transparent);
}
.cell__order {
  font-family: var(--font-num);
  font-size: 10px;
  letter-spacing: .1em;
  font-variant-numeric: tabular-nums;
  color: var(--text-3);
}
.cell__lines { width: 42%; color: var(--text-1); }
.cell.is-selected .cell__lines { color: var(--accent); }
.cell__name { font-size: var(--t-sm); font-weight: 600; letter-spacing: .04em; color: var(--text-1); }
.atlas__empty { grid-column: 1 / -1; padding: var(--s-7) 0; text-align: center; color: var(--text-3); }

.atlas__detail {
  position: sticky;
  top: 88px;
  padding: var(--s-5);
  background: var(--surface-1);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-1), var(--sheen);
}
.detail__head { display: flex; align-items: baseline; gap: 10px; }
.detail__num {
  font-family: var(--font-num);
  font-size: 28px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--accent);
}
.detail__head h3 { font-size: 20px; letter-spacing: .04em; color: var(--text-1); }
.detail__lines { width: 92px; margin: var(--s-5) auto; color: var(--text-1); }

.detail__trigrams { margin: 0 0 var(--s-4); display: grid; gap: 7px; }
.detail__trigrams div { display: flex; gap: 12px; font-size: var(--t-sm); }
.detail__trigrams dt { flex: 0 0 auto; color: var(--text-3); }
.detail__trigrams dd { margin: 0; color: var(--text-1); }

.detail__judgment-label {
  font-size: var(--t-micro);
  font-family: var(--font-sans);
  font-weight: 600;
  letter-spacing: .12em;
  color: var(--bronze);
  margin-bottom: var(--s-2);
}
.detail__judgment {
  margin: 0;
  font-size: 15px;
  line-height: 1.9;
  color: var(--text-1);
  white-space: pre-wrap;
}

.detail__source { margin: var(--s-4) 0 0; font-size: var(--t-micro); color: var(--text-3); }
.detail__source a { color: var(--accent); border-bottom: 1px solid var(--accent-line); }
.detail__source a:hover { border-bottom-color: var(--accent); }

.detail__status {
  margin: var(--s-3) 0 0;
  padding: 9px 11px;
  font-size: var(--t-micro);
  line-height: 1.7;
  color: var(--text-2);
  background: var(--warning-soft);
  border-left: 2px solid var(--warning);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
}
.detail__status span { font-weight: 600; color: var(--warning); }
.detail__hint { margin: var(--s-4) 0 0; font-size: var(--t-micro); color: var(--text-3); }

@media (max-width: 980px) {
  .atlas__layout { grid-template-columns: minmax(0, 1fr); }
  .atlas__detail { position: static; }
}
@media (max-width: 700px) {
  .atlas__grid { grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 6px; }
}
@media (max-width: 480px) {
  .atlas__grid { grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 5px; }
  .cell { padding: 9px 4px 7px; }
  .cell__name { font-size: 13px; }
}
</style>
