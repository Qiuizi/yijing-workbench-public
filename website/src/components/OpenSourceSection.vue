<script setup lang="ts">
import type { Dictionary } from '../i18n/zh'
import { asset } from '../links'

defineProps<{ t: Dictionary }>()
</script>

<template>
  <section id="open-source" class="section paper paper-noise">
    <div class="container">
      <div class="section-head section-head--mark">
        <img class="os__mark" :src="asset('brand/mark.svg')" alt="" width="40" height="40" aria-hidden="true" />
        <div>
          <span class="overline">{{ t.openSource.overline }}</span>
          <h2>{{ t.openSource.title }}</h2>
          <p>{{ t.openSource.subheading }}</p>
        </div>
      </div>

      <ul class="os__list">
        <li v-for="(item, i) in t.openSource.items" :key="item.id" class="os__item">
          <span class="os__num">{{ String(i + 1).padStart(2, '0') }}</span>
          <div class="os__body">
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </div>
          <a class="os__link" :href="item.href" target="_blank" rel="noopener">
            {{ item.linkText }}
            <span aria-hidden="true">↗</span>
          </a>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.section-head--mark { display: flex; gap: var(--s-4); align-items: flex-start; }
.os__mark { flex: 0 0 auto; width: 40px; height: 40px; margin-top: 2px; }
.os__list { list-style: none; margin: 0; padding: 0; border-top: 1px solid rgba(43, 51, 46, .22); }
.os__item {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  gap: var(--s-4);
  align-items: center;
  padding: var(--s-5) 0;
  border-bottom: 1px solid rgba(43, 51, 46, .22);
}
.os__num { font-family: var(--font-num); font-size: 15px; letter-spacing: .08em; color: var(--cinnabar); }
.os__body h3 { font-size: 17px; letter-spacing: .03em; color: var(--ink-text); }
.os__body p { margin: 6px 0 0; font-size: 14px; color: var(--ink-text-soft); max-width: 640px; }
.os__link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--cinnabar);
  border: 1px solid rgba(169, 71, 54, .4);
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  transition: background-color .18s ease, color .18s ease;
}
.os__link:hover { background: var(--cinnabar); color: var(--paper-bright); }

@media (max-width: 640px) {
  .os__item { grid-template-columns: 40px minmax(0, 1fr); }
  .os__link { grid-column: 2; justify-self: start; }
}
</style>
