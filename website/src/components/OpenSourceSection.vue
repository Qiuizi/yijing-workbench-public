<script setup lang="ts">
import type { Dictionary } from '../i18n/zh'
import { asset } from '../links'

defineProps<{ t: Dictionary }>()
</script>

<template>
  <section id="open-source" class="section section--blend oss">
    <div class="container">
      <div class="section-head section-head--mark">
        <img class="oss__mark" :src="asset('brand/mark.svg')" alt="" width="38" height="38" aria-hidden="true" />
        <div>
          <span class="overline">{{ t.openSource.overline }}</span>
          <h2>{{ t.openSource.title }}</h2>
          <p>{{ t.openSource.subheading }}</p>
        </div>
      </div>

      <ul class="oss__list">
        <li v-for="(item, i) in t.openSource.items" :key="item.id" class="oss__item">
          <span class="oss__num num">{{ String(i + 1).padStart(2, '0') }}</span>
          <div class="oss__body">
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </div>
          <a class="oss__link" :href="item.href" target="_blank" rel="noopener">
            {{ item.linkText }}
            <span class="oss__arrow" aria-hidden="true">↗</span>
          </a>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.oss {
  --tone: var(--bg);
  --tone-prev: var(--surface-2);
}

.section-head--mark { display: flex; gap: var(--s-4); align-items: flex-start; }
.oss__mark { flex: 0 0 auto; width: 38px; height: 38px; margin-top: 4px; color: var(--bronze); opacity: .85; }

/* 列表不用整块卡片，靠发丝线分区，阅读更安静 */
.oss__list { list-style: none; margin: 0; padding: 0; }
.oss__item {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  gap: var(--s-4);
  align-items: center;
  padding: var(--s-5) 4px;
  border-top: 1px solid var(--line);
  transition: background-color var(--dur-2) var(--ease-out);
}
.oss__item:last-child { border-bottom: 1px solid var(--line); }
.oss__item:hover { background: color-mix(in srgb, var(--surface-1) 55%, transparent); }
.oss__num {
  font-family: var(--font-num);
  font-size: var(--t-sm);
  letter-spacing: .06em;
  font-variant-numeric: tabular-nums;
  color: var(--bronze);
}
.oss__body h3 { font-size: var(--t-h3); letter-spacing: .02em; color: var(--text-1); }
.oss__body p { margin: 6px 0 0; font-size: var(--t-sm); line-height: 1.75; color: var(--text-2); max-width: 620px; }
.oss__link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-family: var(--font-sans);
  font-size: var(--t-xs);
  color: var(--accent);
  border: 1px solid var(--accent-line);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  transition: background-color var(--dur-1) var(--ease-out), color var(--dur-1) var(--ease-out), border-color var(--dur-1) var(--ease-out);
}
.oss__link:hover { background: var(--accent); color: var(--c-paper-50); border-color: var(--accent); }
.oss__arrow { display: inline-block; transition: transform var(--dur-1) var(--ease-out); }
.oss__link:hover .oss__arrow { transform: translate(1px, -1px); }

@media (max-width: 640px) {
  .oss__item { grid-template-columns: 38px minmax(0, 1fr); row-gap: 10px; }
  .oss__link { grid-column: 2; justify-self: start; }
}
</style>
