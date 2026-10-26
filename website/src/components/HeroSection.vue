<script setup lang="ts">
import type { Dictionary } from '../i18n/zh'
import { asset, LINKS } from '../links'

defineProps<{ t: Dictionary }>()

const shot = asset('shots/workbench-result.png')
</script>

<template>
  <section id="hero" class="hero">
    <div class="hero__wash" aria-hidden="true"></div>
    <div class="hero__rule" aria-hidden="true"></div>
    <div class="container hero__grid">
      <div class="hero__copy">
        <p class="overline reveal">{{ t.hero.overline }}</p>
        <h1 class="reveal" style="animation-delay:.06s">{{ t.hero.title }}</h1>
        <p class="hero__latin reveal" style="animation-delay:.12s">{{ t.hero.titleLatin }}</p>
        <p class="hero__slogan reveal" style="animation-delay:.18s">{{ t.hero.slogan }}</p>
        <p class="hero__sub reveal" style="animation-delay:.24s">{{ t.hero.sub }}</p>

        <div class="hero__cta reveal" style="animation-delay:.3s">
          <a class="btn btn--primary" :href="LINKS.download">{{ t.hero.ctaPrimary }}</a>
          <a class="btn btn--ghost" :href="LINKS.repo" target="_blank" rel="noopener">
            <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
            {{ t.hero.ctaSecondary }}
          </a>
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
              :alt="t.hero.shotLabel"
              width="1600"
              height="1000"
              fetchpriority="high"
            />
          </div>
          <figcaption class="shot__cap">
            <span class="shot__cap-label">{{ t.hero.shotLabel }}</span>
          </figcaption>
          <img class="shot__seal" :src="asset('brand/seal.svg')" alt="" width="44" height="44" aria-hidden="true" />
        </figure>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  padding-block: clamp(44px, 5.4vw, 78px) clamp(42px, 5vw, 72px);
  background: var(--bg);
}
/* 极淡的墨色晕染：左上落一点赭，右下收一点黛 */
.hero__wash {
  position: absolute;
  inset: -10% -10% auto -10%;
  height: 120%;
  pointer-events: none;
  background:
    radial-gradient(58% 46% at 12% 4%, color-mix(in srgb, var(--accent) 7%, transparent), transparent 70%),
    radial-gradient(48% 40% at 92% 22%, color-mix(in srgb, var(--c-ink-700) 8%, transparent), transparent 72%);
  opacity: .9;
}
:root[data-theme='dark'] .hero__wash {
  background:
    radial-gradient(58% 46% at 10% 0%, color-mix(in srgb, var(--accent) 13%, transparent), transparent 68%),
    radial-gradient(50% 44% at 92% 18%, color-mix(in srgb, var(--bronze) 8%, transparent), transparent 72%);
}
/* 顶部一条渐隐的铜金发丝，替代原来的硬边框 */
.hero__rule {
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--bronze) 26%, var(--accent) 50%, var(--bronze) 74%, transparent);
  opacity: .32;
}

.hero__grid {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.04fr);
  gap: clamp(36px, 5.4vw, 76px);
  align-items: center;
}

.overline {
  margin: 0 0 var(--s-4);
  font-family: var(--font-sans);
  font-size: var(--t-micro);
  font-weight: 600;
  letter-spacing: var(--ls-overline);
  color: var(--bronze);
}
h1 {
  margin: 0;
  font-size: var(--t-display);
  line-height: var(--lh-display);
  letter-spacing: var(--ls-display);
  color: var(--text-1);
  font-weight: 600;
}
.hero__latin {
  margin: var(--s-2) 0 0;
  font-family: var(--font-num);
  font-size: var(--t-xs);
  letter-spacing: .3em;
  text-transform: uppercase;
  color: var(--bronze);
  opacity: .9;
}
.hero__slogan {
  margin: clamp(24px, 3vw, 36px) 0 0;
  font-size: var(--t-lead);
  line-height: 1.62;
  color: var(--text-1);
  letter-spacing: .06em;
  padding-left: var(--s-4);
  border-left: 2px solid var(--accent);
  border-image: linear-gradient(180deg, var(--accent), color-mix(in srgb, var(--accent) 30%, transparent)) 1;
}
.hero__sub {
  margin: var(--s-4) 0 0;
  max-width: 540px;
  color: var(--text-2);
  font-size: var(--t-sm);
  line-height: 1.85;
}
.hero__cta { display: flex; flex-wrap: wrap; gap: 12px; margin-top: clamp(26px, 3vw, 34px); }

.hero__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  list-style: none;
  margin: var(--s-6) 0 0;
  padding: 0;
}
.hero__meta li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-sans);
  font-size: var(--t-micro);
  letter-spacing: .1em;
  font-variant-numeric: tabular-nums;
  color: var(--text-3);
}
.hero__meta li + li::before {
  content: '';
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--line-strong);
}

.hero__figure { display: flex; justify-content: center; }
.shot { position: relative; margin: 0; width: 100%; max-width: 600px; }
/* 温润咬合：纸色卡纸 + 发丝边 + 极轻的内高光，不用粗黑框 */
.shot__frame {
  position: relative;
  background: var(--surface-1);
  padding: 10px;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-2), var(--sheen);
}
.shot__frame::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background: linear-gradient(140deg, color-mix(in srgb, var(--bronze) 10%, transparent), transparent 42%);
}
.shot__frame img {
  width: 100%;
  height: auto;
  border: 1px solid var(--line);
  border-radius: 2px;
}
.shot__cap { display: flex; justify-content: flex-end; padding: 10px 2px 0; }
/* 夜间把亮底截图压一档，避免整屏最亮的东西是一张图 */
:root[data-theme='dark'] .shot__frame { background: var(--surface-2); }
:root[data-theme='dark'] .shot__frame img { filter: brightness(.9) saturate(.94); }
.shot__cap-label {
  font-family: var(--font-sans);
  font-size: var(--t-micro);
  letter-spacing: .12em;
  color: var(--text-3);
}
.shot__seal {
  position: absolute;
  top: -12px;
  right: -12px;
  width: 44px;
  height: 44px;
  transform: rotate(-4deg);
  filter: drop-shadow(0 6px 14px color-mix(in srgb, var(--accent) 22%, transparent));
}

@media (max-width: 900px) {
  .hero__grid { grid-template-columns: minmax(0, 1fr); gap: clamp(26px, 5vw, 40px); }
  .hero { padding-block: clamp(36px, 6vw, 56px) clamp(40px, 7vw, 64px); }
  .shot__seal { width: 38px; height: 38px; top: -9px; right: -9px; }
}
</style>
