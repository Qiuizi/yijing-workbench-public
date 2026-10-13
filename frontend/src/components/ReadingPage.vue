<script setup lang="ts">
import { computed } from 'vue'
import TraditionalReading from './TraditionalReading.vue'
import type { Divination } from '../types'
import { specialLineForCast } from '../specialLine'

const props = defineProps<{ divination: Divination | null }>()
const emit = defineEmits<{ startCasting: [] }>()
const lineNames = ['初爻', '二爻', '三爻', '四爻', '五爻', '上爻']
const specialLine = computed(() => props.divination ? specialLineForCast(props.divination.base_hexagram, props.divination.lines) : null)
const movingLines = computed(() => props.divination
  ? props.divination.moving_positions.map((position) => ({ position, text: props.divination!.base_hexagram.line_texts[position - 1] }))
  : [])
</script>

<template>
  <section v-if="divination" class="reading-page">
    <div class="reading-page__header">
      <span class="section-index">02</span>
      <div><p class="overline">TRADITIONAL READING</p><h2>本次取辞与原文</h2><p>先看本次为何选取这些内容，再对照本卦、动爻与之卦原文。</p></div>
    </div>
    <TraditionalReading v-if="divination.traditional_reading" :reading="divination.traditional_reading" />
    <div class="reading-page__grid">
      <article class="panel reading-card">
        <span class="reading-card__source-label">本地典籍原文 · 本卦</span>
        <span class="text-card__eyebrow">第{{ divination.base_hexagram.wenwang_order }}卦 · {{ divination.base_hexagram.upper_trigram.name }}上{{ divination.base_hexagram.lower_trigram.name }}下</span>
        <h3>{{ divination.base_hexagram.title }}</h3>
        <blockquote class="reading-quote"><p>{{ divination.base_hexagram.judgment }}</p><span>卦辞</span></blockquote>
        <div class="text-divider"><span>本次动爻原文</span><i></i></div>
        <div v-if="movingLines.length" class="line-text-list">
          <blockquote v-for="line in movingLines" :key="line.position" class="reading-quote reading-quote--line"><p>{{ line.text }}</p><span>{{ lineNames[line.position - 1] }}</span></blockquote>
        </div>
        <p v-else class="quiet-note">本卦无动爻。</p>
        <blockquote v-if="specialLine" class="reading-quote reading-quote--special"><p>{{ specialLine.text }}</p><span>{{ specialLine.name }}</span></blockquote>
        <a class="source-link" :href="divination.base_hexagram.source_url" target="_blank" rel="noreferrer">经文来源 · 维基文库固定页面</a>
      </article>
      <article class="panel reading-card reading-card--changed">
        <span class="reading-card__source-label">本地典籍原文 · 之卦对照</span>
        <span class="text-card__eyebrow">第{{ divination.changed_hexagram.wenwang_order }}卦 · {{ divination.changed_hexagram.upper_trigram.name }}上{{ divination.changed_hexagram.lower_trigram.name }}下</span>
        <h3>{{ divination.changed_hexagram.title }}</h3>
        <blockquote class="reading-quote"><p>{{ divination.changed_hexagram.judgment }}</p><span>卦辞</span></blockquote>
        <p class="quiet-note reading-card__note">之卦卦辞用于原文对照；应用不另造动爻数量的断语。</p>
        <a class="source-link" :href="divination.changed_hexagram.source_url" target="_blank" rel="noreferrer">经文来源 · 维基文库固定页面</a>
      </article>
    </div>
  </section>
  <section v-else class="page-panel panel page-empty">
    <span class="text-empty__mark">《易》</span><h2>先起一卦，再看本次取辞</h2>
    <p>完成起卦后，这里会说明本次为什么查看这些经文，并展示本卦、动爻和之卦原文。</p>
    <el-button type="primary" @click="emit('startCasting')">前往起卦</el-button>
  </section>
</template>
