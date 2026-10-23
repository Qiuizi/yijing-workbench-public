<script setup lang="ts">
import type { Dictionary } from '../i18n/zh'
import { BASE, LINKS } from '../links'

defineProps<{ locale: 'zh' | 'en'; t: Dictionary }>()
</script>

<template>
  <footer class="site-footer shell">
    <div class="container footer__grid">
      <div class="footer__brand">
        <a class="footer__mark" :href="BASE" :aria-label="t.footer.homeLabel">
          <img :src="BASE + 'brand/mark-inverse.svg'" alt="" width="44" height="44" />
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
        <span>{{ t.footer.version }}</span>
        <span>{{ t.footer.author }}</span>
        <span>{{ t.footer.copyright }}</span>
      </div>
    </div>
    <div class="container footer__bottom">
      <hr class="rule-gold" />
      <p>{{ t.footer.disclaimer }}</p>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  padding: var(--s-8) 0 var(--s-6);
  background: var(--ink-950);
  border-top: 1px solid rgba(201, 162, 39, .22);
}
.footer__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: var(--s-6);
  align-items: center;
}
.footer__brand { display: flex; align-items: center; gap: 16px; }
.footer__mark { flex: 0 0 auto; }
.footer__mark img { width: 44px; height: 44px; }
.footer__brand strong { font-size: 17px; letter-spacing: .04em; color: var(--shell-text); }
.footer__brand p { margin: 4px 0 0; font-size: 12.5px; color: var(--shell-text-soft); }

.footer__nav { display: flex; flex-wrap: wrap; gap: 20px; }
.footer__nav a { font-family: var(--font-sans); font-size: 13px; color: var(--shell-text-soft); transition: color .18s ease; }
.footer__nav a:hover { color: var(--gold-300); }

.footer__meta { display: flex; flex-wrap: wrap; gap: 14px; justify-content: flex-end; }
.footer__meta span { font-family: var(--font-num); font-size: 12px; letter-spacing: .05em; color: #a89b74; }

.footer__bottom { padding-top: var(--s-5); }
.footer__bottom .rule-gold { margin-bottom: var(--s-4); }
.footer__bottom p { margin: 0; font-size: 12px; color: var(--shell-text-soft); }

@media (max-width: 820px) {
  .footer__grid { grid-template-columns: 1fr; gap: var(--s-5); }
  .footer__meta { justify-content: flex-start; }
}
</style>
