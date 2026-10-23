<script setup lang="ts">
import type { Dictionary } from '../i18n/zh'
import { asset, LINKS } from '../links'

defineProps<{ t: Dictionary }>()

const shot = asset('shots/workbench-result.png')
</script>

<template>
  <section id="hero" class="hero shell grain-dark">
    <div class="container hero__grid">
      <div class="hero__copy">
        <p class="overline reveal">{{ t.hero.overline }}</p>
        <h1 class="reveal" style="animation-delay:.06s">{{ t.hero.title }}</h1>
        <p class="hero__latin reveal" style="animation-delay:.12s">{{ t.hero.titleLatin }}</p>
        <p class="hero__slogan reveal" style="animation-delay:.18s">{{ t.hero.slogan }}</p>
        <p class="hero__sub reveal" style="animation-delay:.24s">{{ t.hero.sub }}</p>

        <div class="hero__cta reveal" style="animation-delay:.3s">
          <a class="btn btn--primary" :href="LINKS.download">{{ t.hero.ctaPrimary }}</a>
          <a class="btn btn--ghost" :href="LINKS.repo" target="_blank" rel="noopener">{{ t.hero.ctaSecondary }}</a>
        </div>

        <ul class="hero__meta reveal" style="animation-delay:.36s">
          <li>{{ t.hero.badgeVersion }}</li>
          <li>{{ t.hero.badgePlatform }}</li>
          <li>{{ t.hero.badgeLocal }}</li>
        </ul>
      </div>

      <div class="hero__figure reveal" style="animation-delay:.2s">
        <figure class="shot">
          <div class="shot__frame">
            <img
              :src="shot"
              :alt="t.hero.shotLabel + ' · ' + t.hero.badgeVersion"
              width="1600"
              height="1000"
              fetchpriority="high"
            />
          </div>
          <figcaption class="shot__cap">
            <span class="shot__cap-label">{{ t.hero.shotLabel }} · {{ t.hero.badgeVersion }}</span>
          </figcaption>
          <img class="shot__seal" :src="asset('brand/seal.svg')" alt="" width="48" height="48" aria-hidden="true" />
        </figure>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero { padding: var(--s-9) 0 var(--s-10); border-bottom: 1px solid rgba(201, 162, 39, .2); }
.hero__grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  gap: clamp(40px, 6vw, 88px);
  align-items: center;
}
.overline {
  margin: 0 0 var(--s-4);
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .3em;
  text-transform: uppercase;
  color: var(--gold-300);
}
h1 {
  margin: 0;
  font-size: clamp(38px, 5.2vw, 64px);
  line-height: 1.12;
  letter-spacing: .03em;
  color: var(--shell-text);
  font-weight: 600;
}
.hero__latin {
  margin: var(--s-3) 0 0;
  font-family: var(--font-num);
  font-size: 15px;
  letter-spacing: .34em;
  text-transform: uppercase;
  color: var(--gold-400);
}
.hero__slogan {
  margin: var(--s-6) 0 0;
  font-size: clamp(20px, 2.4vw, 26px);
  line-height: 1.5;
  color: var(--shell-text);
  letter-spacing: .08em;
  border-left: 2px solid var(--cinnabar);
  padding-left: var(--s-4);
}
.hero__sub {
  margin: var(--s-4) 0 0;
  max-width: 560px;
  color: var(--shell-text-soft);
  font-size: 15px;
}
.hero__cta { display: flex; flex-wrap: wrap; gap: 14px; margin-top: var(--s-6); }

.hero__meta {
  display: flex;
  flex-wrap: wrap;
  list-style: none;
  margin: var(--s-6) 0 0;
  padding: var(--s-4) 0 0;
  border-top: 1px solid rgba(214, 185, 121, .22);
}
.hero__meta li {
  display: inline-flex;
  align-items: center;
  font-family: var(--font-sans);
  font-size: 11px;
  letter-spacing: .1em;
  color: rgba(185, 192, 183, .72);
}
.hero__meta li + li {
  border-left: 1px solid rgba(214, 185, 121, .28);
  margin-left: 14px;
  padding-left: 14px;
}

.hero__figure { display: flex; justify-content: center; }
.shot {
  position: relative;
  margin: 0;
  width: 100%;
  max-width: 560px;
}
.shot__frame {
  background: var(--paper-bright);
  padding: 12px;
  border: 1px solid var(--gold-400);
  border-radius: 3px;
  box-shadow:
    inset 0 0 26px rgba(43, 51, 46, .08),
    0 26px 70px rgba(0, 0, 0, .5);
}
.shot__frame img {
  width: 100%;
  height: auto;
  display: block;
  border: 1px solid rgba(43, 51, 46, .35);
  border-radius: 2px;
}
.shot__cap { display: flex; justify-content: flex-end; padding: 10px 4px 0; }
.shot__cap-label {
  font-family: var(--font-sans);
  font-size: 11px;
  letter-spacing: .14em;
  color: var(--gold-300);
}
.shot__seal {
  position: absolute;
  top: -14px;
  right: -14px;
  width: 48px;
  height: 48px;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, .4));
}

@media (max-width: 900px) {
  .hero__grid { grid-template-columns: 1fr; }
  .hero__figure { order: -1; }
  .shot__seal { width: 40px; height: 40px; top: -10px; right: -10px; }
}
</style>
