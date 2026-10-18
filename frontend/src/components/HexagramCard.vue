<script setup lang="ts">
import { computed } from 'vue'
import HexagramGlyph from './HexagramGlyph.vue'
import type { DivinationLine, Hexagram } from '../types'

const props = withDefaults(defineProps<{
  hexagram: Hexagram
  lines: DivinationLine[]
  movingPositions: number[]
  changed?: boolean
}>(), { changed: false })

const ordinal = computed(() => String(props.hexagram.wenwang_order).padStart(2, '0'))
</script>

<template>
  <article class="hexagram-card" :class="{ 'hexagram-card--changed': changed }">
    <div class="hexagram-card__eyebrow">
      <span>{{ changed ? '之卦' : '本卦' }}</span>
      <span class="hexagram-card__ordinal">第 {{ ordinal }} 卦</span>
    </div>
    <h2 class="hexagram-card__title">{{ hexagram.title }}</h2>
    <div class="hexagram-card__trigrams" aria-label="上下卦">
      <span>{{ hexagram.upper_trigram.name }}上 · {{ hexagram.upper_trigram.image }}</span>
      <span class="trigram-separator">/</span>
      <span>{{ hexagram.lower_trigram.name }}下 · {{ hexagram.lower_trigram.image }}</span>
    </div>

    <HexagramGlyph class="hexagram-card__drawing" :code="hexagram.binary_code" :label="hexagram.title" :lines="lines" :moving-positions="movingPositions" />
    <div class="hexagram-card__legend">
      <span><i class="legend-mark legend-mark--yang"></i>阳爻</span>
      <span><i class="legend-mark legend-mark--yin"></i>阴爻</span>
      <span v-if="movingPositions.length"><i class="legend-mark legend-mark--moving"></i>动爻</span>
    </div>
    <div class="hexagram-card__binary">编码 · {{ hexagram.binary_code.split('').join(' ') }}</div>
  </article>
</template>

