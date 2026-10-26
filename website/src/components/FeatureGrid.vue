<script setup lang="ts">
import type { Dictionary } from '../i18n/zh'

defineProps<{ t: Dictionary }>()

// 统一：32 视框、stroke 1.3、round 末端，图标在 34px 底座里视觉重量一致。
const icons: Record<string, string> = {
  coins:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" aria-hidden="true"><circle cx="10" cy="17" r="5.6"/><circle cx="22" cy="17" r="5.6"/><circle cx="16" cy="10" r="5.6"/><rect x="9" y="16" width="2" height="2" fill="currentColor" stroke="none"/><rect x="21" y="16" width="2" height="2" fill="currentColor" stroke="none"/><rect x="15" y="9" width="2" height="2" fill="currentColor" stroke="none"/></svg>',
  manual:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" aria-hidden="true"><line x1="7" y1="9" x2="25" y2="9"/><line x1="7" y1="16" x2="13" y2="16"/><line x1="19" y1="16" x2="25" y2="16"/><line x1="7" y1="23" x2="25" y2="23"/></svg>',
  reading:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 8a3 3 0 0 1 3-3h19v20H8a3 3 0 0 0-3 3z"/><path d="M5 25a3 3 0 0 1 3-3h19"/><line x1="9" y1="9" x2="16" y2="9"/><line x1="9" y1="13" x2="20" y2="13"/></svg>',
  najia:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><rect x="6.5" y="6.5" width="19" height="19" rx="1"/><line x1="16" y1="6.5" x2="16" y2="25.5"/><line x1="6.5" y1="16" x2="25.5" y2="16"/><circle cx="11.2" cy="11.2" r="1.3" fill="currentColor" stroke="none"/><circle cx="20.8" cy="20.8" r="1.3" fill="currentColor" stroke="none"/></svg>',
  atlas:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" aria-hidden="true"><rect x="6.5" y="6.5" width="8" height="8" rx="1"/><rect x="17.5" y="6.5" width="8" height="8" rx="1"/><rect x="6.5" y="17.5" width="8" height="8" rx="1"/><rect x="17.5" y="17.5" width="8" height="8" rx="1"/></svg>',
  history:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" aria-hidden="true"><circle cx="16" cy="16" r="9"/><line x1="16" y1="11" x2="16" y2="16"/><line x1="16" y1="16" x2="21" y2="18"/></svg>',
  ai:
    '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" aria-hidden="true"><path d="M16 5c1.2 5.6 4.4 8.8 10 10-5.6 1.2-8.8 4.4-10 10-1.2-5.6-4.4-8.8-10-10 5.6-1.2 8.8-4.4 10-10z"/></svg>',
}
</script>

<template>
  <section id="features" class="section section--blend features">
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
            <span class="feature__num num">{{ String(i + 1).padStart(2, '0') }}</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.desc }}</p>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.features {
  --tone: var(--bg);
  --tone-prev: var(--surface-2);
}

.features__grid {
  /* 12 栏栅格：4 + 3 排布，第二行三张各占 4 栏正好填满 */
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 14px;
}
.feature {
  position: relative;
  grid-column: span 3;
  padding: var(--s-5) var(--s-5) var(--s-6);
  background: var(--surface-1);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  box-shadow: var(--sheen);
  transition:
    border-color var(--dur-2) var(--ease-out),
    background-color var(--dur-2) var(--ease-out),
    box-shadow var(--dur-2) var(--ease-out),
    transform var(--dur-1) var(--ease-out);
}
.feature:nth-child(5),
.feature:nth-child(6),
.feature:nth-child(7) { grid-column: span 4; }

.feature::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  opacity: 0;
  background: var(--glow);
  transition: opacity var(--dur-2) var(--ease-out);
}
.feature:hover {
  border-color: var(--accent-line);
  transform: translateY(-1px);
  box-shadow: var(--shadow-1), var(--sheen);
}
.feature:hover::after { opacity: 1; }

.feature__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--s-4);
}
.feature__icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  color: var(--bronze);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
}
.feature__icon :deep(svg) { width: 20px; height: 20px; }
.feature__num {
  font-family: var(--font-num);
  font-size: var(--t-micro);
  letter-spacing: .12em;
  font-variant-numeric: tabular-nums;
  color: var(--text-3);
}
.feature h3 {
  font-size: var(--t-h3);
  font-weight: 600;
  color: var(--text-1);
  letter-spacing: .03em;
  line-height: 1.5;
}
.feature p {
  margin: var(--s-2) 0 0;
  font-size: var(--t-sm);
  line-height: 1.78;
  color: var(--text-2);
}

@media (max-width: 1023px) {
  .feature,
  .feature:nth-child(5),
  .feature:nth-child(6) { grid-column: span 6; }
  .feature:nth-child(7) { grid-column: span 12; }
}
@media (max-width: 620px) {
  .feature,
  .feature:nth-child(5),
  .feature:nth-child(6),
  .feature:nth-child(7) { grid-column: span 12; }
  .features__grid { gap: 10px; }
}
</style>
