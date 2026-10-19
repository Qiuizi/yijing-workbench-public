<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Hexagram, LearningGuide } from '../types'
import HexagramGlyph from './HexagramGlyph.vue'
const props = defineProps<{ hexagram: Hexagram; guide?: LearningGuide }>()
const emit = defineEmits<{ open: [id: number]; back: [] }>()
const approvedGuide = computed(() =>
  props.guide?.review_status === 'reviewed' ? props.guide : undefined,
)
const heading = ref<HTMLElement | null>(null)
const expanded = ref<number[]>([])
watch(
  () => props.hexagram.wenwang_order,
  () => {
    expanded.value = []
  },
)
const count = computed(() => (props.hexagram.special_line ? 7 : 6))
function toggle(index: number) {
  expanded.value = expanded.value.includes(index)
    ? expanded.value.filter((value) => value !== index)
    : [...expanded.value, index]
}
function toggleAll() {
  expanded.value =
    expanded.value.length === count.value
      ? []
      : Array.from({ length: count.value }, (_, index) => index)
}
defineExpose({
  focusHeading: () => heading.value?.focus({ preventScroll: true }),
})
</script>
<template>
  <article class="learning-reader learning-article">
    <nav class="learning-reader__nav" aria-label="卦象阅读导航">
      <button type="button" @click="emit('back')">← 返回六十四卦</button>
      <div>
        <button
          type="button"
          :disabled="hexagram.wenwang_order === 1"
          @click="emit('open', hexagram.wenwang_order - 1)"
        >
          上一卦</button
        ><span>{{ String(hexagram.wenwang_order).padStart(2, '0') }} / 64</span
        ><button
          type="button"
          :disabled="hexagram.wenwang_order === 64"
          @click="emit('open', hexagram.wenwang_order + 1)"
        >
          下一卦 →
        </button>
      </div>
    </nav>
    <header class="learning-reader__masthead">
      <div>
        <p class="learning-eyebrow">
          第 {{ String(hexagram.wenwang_order).padStart(2, '0') }} 卦 · 《周易》
        </p>
        <h1 ref="heading" tabindex="-1">{{ hexagram.title }}</h1>
        <p v-if="approvedGuide?.one_liner" class="learning-reader__one-liner">{{ approvedGuide.one_liner }}</p>
        <p class="learning-reader__trigrams">
          {{ hexagram.upper_trigram.name }}上 ·
          {{ hexagram.lower_trigram.name }}下
          <span
            >{{ hexagram.upper_trigram.image }} /
            {{ hexagram.lower_trigram.image }}</span
          >
        </p>
      </div>
      <div class="learning-reader__figure">
        <HexagramGlyph
          :code="hexagram.binary_code"
          :label="hexagram.title"
          compact
        /><span
          >观象 · {{ hexagram.upper_trigram.name }}上{{
            hexagram.lower_trigram.name
          }}下</span
        >
      </div>
    </header>
    <div class="learning-reader__body">
      <section class="learning-reader__guide" aria-label="编辑导读">
        <template v-if="approvedGuide"
          ><span class="learning-content-label"
            >编辑导读 · 现代阐释</span
          >
          <h2>本卦在谈什么？</h2>
          <p>{{ approvedGuide.overview }}</p>
          <a
            v-for="source in approvedGuide.references"
            :key="source.url"
            :href="source.url"
            target="_blank"
            rel="noreferrer"
            >{{ source.title }} ↗</a
          ></template
        ><template v-else
          ><span class="learning-content-label">原文阅读</span>
          <p>
            导读整理中。先读卦辞，再从初爻至上爻，依次阅读经典原文。
          </p></template
        >
      </section>
      <section class="learning-reader__judgment">
        <div class="learning-reading-label">
          <h2>卦辞</h2>
          <span>经典原文</span>
        </div>
        <blockquote>{{ hexagram.judgment }}</blockquote>
        <a :href="hexagram.source_url" target="_blank" rel="noreferrer"
          >查看固定来源 ↗</a
        >
      </section>
      <section class="learning-reader__lines">
        <div class="learning-reading-label">
          <h2>逐爻阅读</h2>
          <span>初爻至上爻</span
          ><button type="button" @click="toggleAll">
            {{ expanded.length === count ? '全部收起' : '全部展开' }}
          </button>
        </div>
        <div
          v-for="(text, index) in hexagram.line_texts"
          :key="index"
          class="learning-reader__line"
        >
          <button
            type="button"
            :aria-expanded="expanded.includes(index)"
            :aria-controls="`learning-line-${index}`"
            @click="toggle(index)"
          >
            <span class="learning-reader__line-index">{{
              String(index + 1).padStart(2, '0')
            }}</span
            ><span class="learning-reader__line-text">{{ text }}</span
            ><span class="learning-reader__line-toggle" aria-hidden="true">{{
              expanded.includes(index) ? '−' : '+'
            }}</span>
          </button>
          <div
            v-if="expanded.includes(index)"
            :id="`learning-line-${index}`"
            class="learning-reader__line-note"
          >
            <span class="learning-content-label"
              >经典原文 · 第{{ index + 1 }}爻</span
            >
            <p v-if="approvedGuide?.line_guides[String(index + 1)]">
              <span class="learning-content-label">编辑说明</span
              >{{ approvedGuide.line_guides[String(index + 1)] }}
            </p>
            <a :href="hexagram.source_url" target="_blank" rel="noreferrer"
              >核对本爻原文来源 ↗</a
            >
          </div>
        </div>
        <div
          v-if="hexagram.special_line"
          class="learning-reader__line learning-reader__special"
        >
          <button
            type="button"
            :aria-expanded="expanded.includes(6)"
            aria-controls="learning-special-line"
            @click="toggle(6)"
          >
            <span class="learning-reader__line-index">{{
              hexagram.special_line.name
            }}</span
            ><span class="learning-reader__line-text">{{
              hexagram.special_line.text
            }}</span
            ><span class="learning-reader__line-toggle" aria-hidden="true">{{
              expanded.includes(6) ? '−' : '+'
            }}</span>
          </button>
          <div
            v-if="expanded.includes(6)"
            id="learning-special-line"
            class="learning-reader__line-note"
          >
            <span class="learning-content-label">经典原文 · 特殊爻辞</span
            ><a
              :href="hexagram.special_line.source_url"
              target="_blank"
              rel="noreferrer"
              >核对原文来源 ↗</a
            >
          </div>
        </div>
      </section>
      <footer class="learning-reader__source">
        <p>
          文本来源：{{ hexagram.text_source }} · 固定修订版
          {{ hexagram.source_revision_id }}
        </p>
        <a :href="hexagram.source_url" target="_blank" rel="noreferrer"
          >维基文库原文与许可 ↗</a
        >
        <p>字形与标点依收录版本。编辑导读独立于经典原文。</p>
      </footer>
      <nav class="learning-reader__continue" aria-label="继续学习">
        <button
          type="button"
          :disabled="hexagram.wenwang_order === 1"
          @click="emit('open', hexagram.wenwang_order - 1)"
        >
          ← 上一卦</button
        ><button type="button" @click="emit('back')">返回图鉴</button
        ><button
          type="button"
          :disabled="hexagram.wenwang_order === 64"
          @click="emit('open', hexagram.wenwang_order + 1)"
        >
          下一卦 →
        </button>
      </nav>
    </div>
  </article>
</template>
