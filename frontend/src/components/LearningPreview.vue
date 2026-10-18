<script setup lang="ts">
import HexagramGlyph from './HexagramGlyph.vue'
import type { Hexagram, HexagramSummary } from '../types'
defineProps<{
  entry: HexagramSummary
  hexagram: Hexagram | null
  loading: boolean
  error: string
}>()
const emit = defineEmits<{ open: [id: number]; retry: [] }>()
</script>
<template>
  <div
    class="learning-preview"
    :data-preview-id="entry.wenwang_order"
    :aria-busy="loading"
  >
    <div class="learning-preview__top">
      <span>当前卦象</span
      ><span
        >{{ String(entry.wenwang_order).padStart(2, '0') }} <i>/ 64</i></span
      >
    </div>
    <div class="learning-preview__heading">
      <p>{{ entry.upper_trigram.name }}上 · {{ entry.lower_trigram.name }}下</p>
      <h2>{{ entry.title }}</h2>
    </div>
    <div class="learning-preview__figure">
      <HexagramGlyph
        :code="entry.binary_code"
        :label="entry.title"
        compact
      /><span
        >{{ entry.upper_trigram.image }} / {{ entry.lower_trigram.image }}</span
      >
    </div>
    <div class="learning-preview__original">
      <span>卦辞 · 经典原文</span>
      <blockquote v-if="hexagram">{{ hexagram.judgment }}</blockquote>
      <p v-else-if="error" class="learning-preview__error" role="alert">
        {{ error
        }}<button type="button" @click="emit('retry')">重新读取</button>
      </p>
      <p v-else role="status">正在读取本地原文…</p>
    </div>
    <button
      class="learning-preview__read"
      type="button"
      @click="emit('open', entry.wenwang_order)"
    >
      阅读完整原文<span aria-hidden="true">↗</span>
    </button>
    <a
      v-if="hexagram"
      class="learning-preview__source"
      :href="hexagram.source_url"
      target="_blank"
      rel="noreferrer"
      >维基文库固定修订版 ↗</a
    >
  </div>
</template>
