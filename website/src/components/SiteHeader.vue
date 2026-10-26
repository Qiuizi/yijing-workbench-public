<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import type { Dictionary } from '../i18n/zh'
import { BASE, LINKS } from '../links'
import BrandMark from './BrandMark.vue'
import ThemeToggle from './ThemeToggle.vue'

const props = defineProps<{ locale: 'zh' | 'en'; t: Dictionary }>()

const open = ref(false)
const hash = ref('')

function onHash() {
  hash.value = window.location.hash
}
onMounted(() => {
  hash.value = window.location.hash
  window.addEventListener('hashchange', onHash)
})
onBeforeUnmount(() => window.removeEventListener('hashchange', onHash))

const langHref = computed(() => {
  const target = props.locale === 'zh' ? BASE + 'en/' : BASE
  return target + hash.value
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && open.value) {
    open.value = false
  }
}

const navItems = computed(() => [
  { href: '#features', label: props.t.nav.features },
  { href: '#hexagrams', label: props.t.nav.hexagrams },
  { href: '#download', label: props.t.nav.download },
  { href: '#open-source', label: props.t.nav.openSource },
])

function closeDrawer() {
  open.value = false
}
</script>

<template>
  <header class="site-header" @keydown="onKeydown">
    <div class="container header-inner">
      <a class="brand" :href="BASE" :aria-label="t.hero.title">
        <BrandMark :size="38" tile="auto" />
        <span class="brand__word">
          <strong>{{ t.hero.title }}</strong>
          <small>
            <span class="brand__latin">YIJING WORKBENCH</span>
            <span class="brand__ver">{{ t.hero.badgeVersion }}</span>
          </small>
        </span>
      </a>

      <nav class="nav-desktop" :aria-label="t.nav.primaryLabel">
        <a v-for="item in navItems" :key="item.href" :href="item.href">{{ item.label }}</a>
      </nav>

      <div class="header-actions">
        <ThemeToggle :label-to-dark="t.nav.themeToDark" :label-to-light="t.nav.themeToLight" />
        <a class="btn btn--ghost btn--compact" :href="LINKS.repo" target="_blank" rel="noopener">
          <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
          {{ t.nav.github }}
        </a>
        <a class="btn btn--primary btn--compact" :href="LINKS.download">{{ t.nav.downloadShort }}</a>
        <a class="lang-switch" :href="langHref" :aria-label="t.nav.langLabel">
          <span aria-hidden="true">{{ locale === 'zh' ? 'EN' : '中' }}</span>
        </a>
        <button
          class="nav-toggle"
          type="button"
          :aria-expanded="open ? 'true' : 'false'"
          :aria-label="open ? t.nav.closeMenu : t.nav.openMenu"
          aria-controls="mobile-nav"
          @click="open = !open"
        >
          <span class="nav-toggle__bar" :class="{ 'is-open': open }" />
        </button>
      </div>
    </div>

    <div id="mobile-nav" class="mobile-drawer" :class="{ 'is-open': open }">
      <nav :aria-label="t.nav.mobileLabel">
        <a v-for="item in navItems" :key="item.href" :href="item.href" @click="closeDrawer">{{ item.label }}</a>
      </nav>
      <div class="mobile-drawer__actions">
        <a class="btn btn--primary" :href="LINKS.download" @click="closeDrawer">{{ t.nav.downloadShort }}</a>
        <a class="btn btn--ghost" :href="LINKS.repo" target="_blank" rel="noopener">{{ t.nav.github }}</a>
        <a class="btn btn--ghost" :href="langHref">{{ locale === 'zh' ? 'English' : '中文' }}</a>
      </div>
    </div>
  </header>
</template>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: color-mix(in srgb, var(--bg) 84%, transparent);
  backdrop-filter: blur(14px) saturate(1.06);
  transition: background-color var(--dur-2) var(--ease-soft);
}
/* 分隔不做一刀切：一条两端渐隐的发丝，配合 82% 半透明底 */
.site-header::after {
  content: '';
  position: absolute;
  inset: auto 0 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--line-strong) 12%, var(--line-strong) 88%, transparent);
  opacity: .55;
}

.header-inner {
  display: flex;
  align-items: center;
  gap: 22px;
  height: 68px;
}

.brand { display: inline-flex; align-items: center; gap: 11px; flex: 0 0 auto; }
.brand__word { display: grid; gap: 1px; line-height: 1.16; }
.brand__word strong {
  font-size: 16.5px;
  font-weight: 600;
  letter-spacing: .05em;
  color: var(--text-1);
}
.brand__word small {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-sans);
  font-size: 9.5px;
  font-weight: 500;
  letter-spacing: .13em;
  color: var(--text-3);
}
.brand__ver {
  font-variant-numeric: tabular-nums;
  letter-spacing: .06em;
  color: var(--bronze);
  padding-left: 7px;
  border-left: 1px solid var(--line-strong);
}

.nav-desktop { display: flex; align-items: center; gap: 4px; margin-left: auto; }
.nav-desktop a {
  position: relative;
  padding: 8px 10px;
  font-family: var(--font-sans);
  font-size: var(--t-sm);
  color: var(--text-2);
  letter-spacing: .03em;
  border-radius: var(--radius-sm);
  transition: color var(--dur-1) var(--ease-out), background-color var(--dur-1) var(--ease-out);
}
.nav-desktop a::after {
  content: '';
  position: absolute;
  left: 10px; right: 10px; bottom: 3px;
  height: 1px;
  background: var(--accent);
  transform: scaleX(0);
  transform-origin: left center;
  transition: transform var(--dur-2) var(--ease-out);
}
.nav-desktop a:hover { color: var(--text-1); }
.nav-desktop a:hover::after { transform: scaleX(1); }

.header-actions { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.btn--compact { padding: 8px 14px; font-size: 13px; }

.lang-switch {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px; height: 34px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .04em;
  color: var(--text-2);
  transition: border-color var(--dur-1) var(--ease-out), color var(--dur-1) var(--ease-out), background-color var(--dur-1) var(--ease-out);
}
.lang-switch:hover { border-color: var(--accent-line); color: var(--accent); background: var(--accent-soft); }

.nav-toggle {
  display: none;
  position: relative;
  width: 36px; height: 36px;
  background: transparent;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.nav-toggle__bar, .nav-toggle__bar::before, .nav-toggle__bar::after {
  content: '';
  position: absolute;
  left: 9px; right: 9px;
  height: 1.5px;
  background: var(--text-2);
  transition: transform var(--dur-2) var(--ease-out), top var(--dur-2) var(--ease-out), opacity var(--dur-2) var(--ease-out);
}
.nav-toggle__bar { top: 17px; }
.nav-toggle__bar::before { top: -5px; left: 0; right: 0; }
.nav-toggle__bar::after { top: 5px; left: 0; right: 0; }
.nav-toggle__bar.is-open { background: transparent; }
.nav-toggle__bar.is-open::before { top: 0; transform: rotate(45deg); }
.nav-toggle__bar.is-open::after { top: 0; transform: rotate(-45deg); }

.mobile-drawer { display: none; }

@media (max-width: 980px) {
  .nav-desktop { display: none; }
  .header-actions .btn--ghost, .header-actions .btn--primary { display: none; }
  .nav-toggle { display: inline-block; }
  .header-actions { margin-left: auto; }

  .mobile-drawer {
    display: grid;
    gap: 18px;
    padding: 8px var(--gutter) 26px;
    background: var(--bg);
    max-height: 0;
    overflow: hidden;
    opacity: 0;
    transition: max-height var(--dur-3) var(--ease-out), opacity var(--dur-2) var(--ease-out), padding var(--dur-3) var(--ease-out);
  }
  .mobile-drawer.is-open {
    max-height: calc(100dvh - 68px);
    overflow-y: auto;
    opacity: 1;
  }
  .mobile-drawer nav { display: grid; gap: 2px; }
  .mobile-drawer nav a {
    padding: 12px 0;
    font-family: var(--font-sans);
    font-size: 15px;
    color: var(--text-1);
    border-bottom: 1px solid var(--line);
  }
  .mobile-drawer__actions { display: grid; gap: 10px; }
}

@media (max-width: 420px) {
  .brand__latin { display: none; }
}
</style>
