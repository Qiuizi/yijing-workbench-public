<script setup lang="ts">
import type { Dictionary } from '../i18n/zh'

defineProps<{ t: Dictionary }>()

const icons: Record<string, string> = {
  coins:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><circle cx="10" cy="17" r="5.6"/><circle cx="22" cy="17" r="5.6"/><circle cx="16" cy="10" r="5.6"/><rect x="8.8" y="15.8" width="2.4" height="2.4" fill="currentColor" stroke="none"/><rect x="20.8" y="15.8" width="2.4" height="2.4" fill="currentColor" stroke="none"/><rect x="14.8" y="8.8" width="2.4" height="2.4" fill="currentColor" stroke="none"/></svg>',
  manual:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><line x1="7" y1="9" x2="25" y2="9"/><line x1="7" y1="16" x2="13" y2="16"/><line x1="19" y1="16" x2="25" y2="16"/><line x1="7" y1="23" x2="25" y2="23"/></svg>',
  reading:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" aria-hidden="true"><path d="M5 8a3 3 0 0 1 3-3h19v20H8a3 3 0 0 0-3 3z"/><path d="M5 25a3 3 0 0 1 3-3h19"/><line x1="9" y1="9" x2="16" y2="9"/><line x1="9" y1="13" x2="20" y2="13"/></svg>',
  najia:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><rect x="6" y="6" width="20" height="20"/><line x1="16" y1="6" x2="16" y2="26"/><line x1="6" y1="16" x2="26" y2="16"/><circle cx="11" cy="11" r="1.4" fill="currentColor" stroke="none"/><circle cx="21" cy="21" r="1.4" fill="currentColor" stroke="none"/></svg>',
  atlas:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><rect x="6" y="6" width="8.5" height="8.5"/><rect x="17.5" y="6" width="8.5" height="8.5"/><rect x="6" y="17.5" width="8.5" height="8.5"/><rect x="17.5" y="17.5" width="8.5" height="8.5"/></svg>',
  history:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" aria-hidden="true"><circle cx="16" cy="16" r="9"/><line x1="16" y1="11" x2="16" y2="16"/><line x1="16" y1="16" x2="21" y2="18"/></svg>',
  ai:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" aria-hidden="true"><path d="M16 5c1.2 5.6 4.4 8.8 10 10-5.6 1.2-8.8 4.4-10 10-1.2-5.6-4.4-8.8-10-10 5.6-1.2 8.8-4.4 10-10z"/></svg>',
}
</script>

<template>
  <section id="features" class="section shell grain-dark features">
    <div class="container">
      <div class="section-head">
        <span class="overline">{{ t.features.overline }}</span>
        <h2>{{ t.features.title }}</h2>
        <p>{{ t.features.subheading }}</p>
      </div>

      <div class="features__grid">
        <article
          v-for="(item, i) in t.features.items"
          :key="item.id"
          class="feature reveal"
          :style="{ animationDelay: (0.05 * i) + 's' }"
        >
          <div class="feature__top">
            <span class="feature__icon" v-html="icons[item.id]" />
            <span class="feature__num">{{ String(i + 1).padStart(2, '0') }}</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.desc }}</p>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.features { background: linear-gradient(180deg, var(--ink-950), var(--ink-900)); border-top: 1px solid rgba(201,162,39,.18); border-bottom: 1px solid rgba(201,162,39,.18); }
.features__grid {
  /* 12 栏栅格：7 张卡片按 4 + 3 排布，第二行三张各占 4 栏正好填满，
     不再用 auto-fill 留下空轨道造成的空洞。 */
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
}
.feature {
  grid-column: span 3;
}
.feature:nth-child(5),
.feature:nth-child(6),
.feature:nth-child(7) {
  grid-column: span 4;
}
.feature {
  position: relative;
  padding: var(--s-5) var(--s-5) var(--s-6);
  background: var(--ink-900);
  border: 1px solid rgba(201, 162, 39, .2);
  border-radius: 3px;
  transition: background-color .22s ease, border-color .22s ease, transform .22s ease;
}
.feature:hover { background: var(--bronze-800); border-color: rgba(201, 162, 39, .45); transform: translateY(-2px); }
.feature__top { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: var(--s-4); }
.feature__icon { width: 34px; height: 34px; color: var(--gold-400); }
.feature__icon :deep(svg) { width: 100%; height: 100%; }
.feature__num {
  font-family: var(--font-num);
  font-size: 12px;
  letter-spacing: .16em;
  color: rgba(214, 185, 121, .5);
}
.feature h3 { font-size: 17px; font-weight: 600; color: var(--shell-text); letter-spacing: .04em; }
.feature p { margin: var(--s-2) 0 0; font-size: 13.5px; line-height: 1.75; color: var(--shell-text-soft); }

@media (max-width: 1023px) {
  .feature,
  .feature:nth-child(5),
  .feature:nth-child(6) {
    grid-column: span 6;
  }
  /* 第七张横跨整行，避免 2 栏布局下最后一个格子空缺。 */
  .feature:nth-child(7) {
    grid-column: span 12;
  }
}
@media (max-width: 620px) {
  .feature,
  .feature:nth-child(5),
  .feature:nth-child(6),
  .feature:nth-child(7) {
    grid-column: span 12;
  }
}
</style>
