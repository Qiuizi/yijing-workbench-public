<script setup lang="ts">
import type { Page } from '../navigation'
import BrandMark from './BrandMark.vue'

const emit = defineEmits<{ navigate: [page: Page] }>()
const pages = [
  { id: 'divination', label: '起卦' },
  { id: 'learning', label: '学习' },
  { id: 'history', label: '历史' },
  { id: 'settings', label: '设置' },
] as const
</script>
<template>
  <header class="learning-header">
    <a
      href="#/learning"
      class="learning-brand"
      aria-label="易经学习首页"
      @click.prevent="emit('navigate', 'learning')"
    >
      <BrandMark :size="26" />
      <span class="learning-brand__name">易经</span>
      <span class="learning-brand__sub">起卦工作台</span>
    </a>
    <nav class="learning-top-nav" aria-label="主导航">
      <button
        v-for="page in pages"
        :key="page.id"
        type="button"
        :aria-current="page.id === 'learning' ? 'page' : undefined"
        @click="emit('navigate', page.id)"
      >
        {{ page.label }}
      </button>
    </nav>
    <span class="learning-header__note">经典原文 · 本地阅读</span>
  </header>
</template>
