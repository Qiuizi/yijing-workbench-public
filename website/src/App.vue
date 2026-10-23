<script setup lang="ts">
import { computed } from 'vue'
import { zh, type Dictionary } from './i18n/zh'
import { en } from './i18n/en'
import SiteHeader from './components/SiteHeader.vue'
import SiteFooter from './components/SiteFooter.vue'
import HeroSection from './components/HeroSection.vue'
import ScreenshotGallery from './components/ScreenshotGallery.vue'
import FeatureGrid from './components/FeatureGrid.vue'
import HexagramAtlas from './components/HexagramAtlas.vue'
import DownloadSection from './components/DownloadSection.vue'
import OpenSourceSection from './components/OpenSourceSection.vue'

const props = defineProps<{ locale: 'zh' | 'en' }>()

const t = computed<Dictionary>(() => (props.locale === 'zh' ? zh : en))
</script>

<template>
  <a class="skip-link" href="#main">{{ t.nav.skipToContent }}</a>
  <SiteHeader :locale="locale" :t="t" />
  <main id="main">
    <HeroSection :t="t" />
    <ScreenshotGallery :t="t" />
    <FeatureGrid :t="t" />
    <HexagramAtlas :t="t" />
    <DownloadSection :t="t" />
    <OpenSourceSection :t="t" />
  </main>
  <SiteFooter :locale="locale" :t="t" />
</template>
