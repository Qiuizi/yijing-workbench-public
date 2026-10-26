<script setup lang="ts">
import type { Dictionary } from '../i18n/zh'
import { BASE, LINKS } from '../links'
import BrandMark from './BrandMark.vue'

defineProps<{ locale: 'zh' | 'en'; t: Dictionary }>()
</script>

<template>
  <footer class="site-footer">
    <div class="container">
      <!-- 封底：与下载区同一种「墨玉块」语言，不用硬边分割页面 -->
      <div class="footer__slab">
        <div class="footer__grid">
          <div class="footer__brand">
            <a class="footer__mark" :href="BASE" :aria-label="t.footer.homeLabel">
              <BrandMark :size="42" tile="ink" />
            </a>
            <div>
              <strong>{{ t.hero.title }}</strong>
              <p>{{ t.footer.tagline }}</p>
            </div>
          </div>

          <nav class="footer__nav" aria-label="Footer">
            <a :href="LINKS.repo" target="_blank" rel="noopener">{{ t.footer.links.repo }}</a>
            <a :href="LINKS.releaseTag" target="_blank" rel="noopener">{{ t.footer.links.release }}</a>
            <a :href="LINKS.license" target="_blank" rel="noopener">{{ t.footer.links.license }}</a>
            <a :href="LINKS.privacy" target="_blank" rel="noopener">{{ t.footer.links.privacy }}</a>
            <a :href="LINKS.source" target="_blank" rel="noopener">{{ t.footer.links.source }}</a>
          </nav>

          <div class="footer__meta">
            <span class="num">{{ t.footer.version }}</span>
            <span>{{ t.footer.author }}</span>
            <span class="num">{{ t.footer.copyright }}</span>
          </div>
        </div>

        <div class="footer__bottom">
          <hr class="rule-gold" />
          <p>{{ t.footer.disclaimer }}</p>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  padding: var(--s-6) 0 var(--s-6);
  background: var(--bg);
}

.footer__slab {
  position: relative;
  padding: clamp(22px, 2.8vw, 34px);
  border-radius: var(--radius-lg);
  color: var(--shell-text);
  background-color: var(--shell-bg);
  border: 1px solid rgba(211, 181, 124, .14);
  box-shadow:
    inset 0 1px 0 rgba(233, 228, 214, .06),
    0 30px 60px -46px rgba(15, 23, 19, .55);
}

:root[data-theme='dark'] .footer__slab {
  --shell-bg: var(--c-night-850);
  border-color: rgba(211, 181, 124, .2);
}

.footer__slab::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background-image: radial-gradient(80% 120% at 6% 0%, rgba(211, 181, 124, .07), transparent 55%);
}

.footer__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: var(--s-6);
  align-items: center;
}
.footer__brand { display: flex; align-items: center; gap: 14px; }
.footer__mark { flex: 0 0 auto; display: block; }
.footer__brand strong {
  font-size: 16px;
  letter-spacing: .05em;
  color: var(--shell-text);
  font-weight: 600;
}
.footer__brand p { margin: 3px 0 0; font-size: var(--t-micro); color: var(--shell-text-soft); }

.footer__nav { display: flex; flex-wrap: wrap; gap: 18px; }
.footer__nav a {
  font-family: var(--font-sans);
  font-size: var(--t-xs);
  color: var(--shell-text-soft);
  transition: color var(--dur-1) var(--ease-out);
}
.footer__nav a:hover { color: var(--shell-bronze); }

.footer__meta { display: flex; flex-wrap: wrap; gap: 14px; justify-content: flex-end; }
.footer__meta span {
  font-family: var(--font-sans);
  font-size: var(--t-micro);
  letter-spacing: .04em;
  font-variant-numeric: tabular-nums;
  color: #9aa294;
}

.footer__bottom { padding-top: var(--s-4); }
.footer__bottom .rule-gold { margin-bottom: var(--s-3); }
.footer__bottom p { margin: 0; font-size: var(--t-micro); line-height: 1.7; color: var(--shell-text-soft); }

@media (max-width: 860px) {
  :root[data-theme='dark'] .footer__slab {
  --shell-bg: var(--c-night-850);
  border-color: rgba(211, 181, 124, .2);
}

.footer__slab::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background-image: radial-gradient(80% 120% at 6% 0%, rgba(211, 181, 124, .07), transparent 55%);
}

.footer__grid { grid-template-columns: 1fr; gap: var(--s-4); }
  .footer__meta { justify-content: flex-start; }
}
</style>
