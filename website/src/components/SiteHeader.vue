<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import type { Dictionary } from '../i18n/zh'
import { BASE, LINKS } from '../links'

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
        <img class="brand__mark" :src="BASE + 'brand/mark-inverse.svg'" alt="" width="40" height="40" />
        <span class="brand__word">
          <strong>{{ t.hero.title }}</strong>
          <small>{{ t.hero.badgeVersion }} · {{ t.hero.badgePlatform }}</small>
        </span>
      </a>

      <nav class="nav-desktop" aria-label="Primary">
        <a v-for="item in navItems" :key="item.href" :href="item.href">{{ item.label }}</a>
      </nav>

      <div class="header-actions">
        <a class="btn btn--ghost btn--compact" :href="LINKS.repo" target="_blank" rel="noopener">
          <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
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
      <nav aria-label="Mobile">
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
  background: rgba(13, 22, 20, .92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(201, 162, 39, .28);
}
.header-inner {
  display: flex;
  align-items: center;
  gap: 24px;
  height: 72px;
}
.brand { display: inline-flex; align-items: center; gap: 12px; flex: 0 0 auto; }
.brand__mark { width: 40px; height: 40px; }
.brand__word { display: grid; line-height: 1.2; }
.brand__word strong { font-size: 17px; letter-spacing: .04em; color: var(--shell-text); font-weight: 600; }
.brand__word small { font-family: var(--font-sans); font-size: 10.5px; letter-spacing: .1em; color: var(--gold-300); }

.nav-desktop { display: flex; align-items: center; gap: 28px; margin-left: auto; }
.nav-desktop a {
  position: relative;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--shell-text-soft);
  letter-spacing: .04em;
  padding: 4px 0;
  transition: color .18s ease;
}
.nav-desktop a::after {
  content: '';
  position: absolute;
  left: 0; right: 100%; bottom: 0;
  height: 1px;
  background: var(--gold-300);
  transition: right .22s ease;
}
.nav-desktop a:hover { color: var(--shell-text); }
.nav-desktop a:hover::after { right: 0; }

.header-actions { display: flex; align-items: center; gap: 12px; margin-left: auto; }
.btn--compact { padding: 9px 16px; font-size: 13px; }
.lang-switch {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px; height: 34px;
  border: 1px solid rgba(214, 185, 121, .4);
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .05em;
  color: var(--gold-300);
  transition: border-color .18s ease, background-color .18s ease;
}
.lang-switch:hover { border-color: var(--gold-300); background: rgba(214, 185, 121, .08); }

.nav-toggle { display: none; position: relative; width: 40px; height: 40px; background: transparent; border: 1px solid rgba(214,185,121,.4); border-radius: var(--radius-sm); cursor: pointer; }
.nav-toggle__bar, .nav-toggle__bar::before, .nav-toggle__bar::after {
  content: '';
  position: absolute;
  left: 10px; right: 10px;
  height: 1.5px;
  background: var(--gold-300);
  transition: transform .2s ease, top .2s ease, opacity .2s ease;
}
.nav-toggle__bar { top: 19px; }
.nav-toggle__bar::before { top: -6px; left: 0; right: 0; }
.nav-toggle__bar::after { top: 6px; left: 0; right: 0; }
.nav-toggle__bar.is-open { background: transparent; }
.nav-toggle__bar.is-open::before { top: 0; transform: rotate(45deg); }
.nav-toggle__bar.is-open::after { top: 0; transform: rotate(-45deg); }

.mobile-drawer { display: none; }

@media (max-width: 900px) {
  .nav-desktop { display: none; }
  .header-actions .btn--ghost, .header-actions .btn--primary { display: none; }
  .nav-toggle { display: inline-block; }
  .lang-switch { order: -1; }

  .mobile-drawer {
    display: grid;
    gap: 20px;
    padding: 12px clamp(20px, 4vw, 56px) 28px;
    border-top: 1px solid rgba(201, 162, 39, .16);
    background: var(--ink-900);
    max-height: 0;
    overflow: hidden;
    opacity: 0;
    transition: max-height .28s ease, opacity .28s ease, padding .28s ease;
  }
  .mobile-drawer.is-open { max-height: 420px; opacity: 1; }
  .mobile-drawer nav { display: grid; gap: 4px; }
  .mobile-drawer nav a {
    padding: 12px 0;
    font-family: var(--font-sans);
    font-size: 16px;
    color: var(--shell-text);
    border-bottom: 1px solid rgba(214, 185, 121, .12);
  }
  .mobile-drawer__actions { display: grid; gap: 12px; }
}
</style>
