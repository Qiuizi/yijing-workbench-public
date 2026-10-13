<script setup lang="ts">
import type { TraditionalReading } from '../types'

defineProps<{ reading: TraditionalReading }>()
</script>

<template>
  <article class="text-card panel traditional-reading">
    <div class="traditional-reading__header">
      <span class="reading-card__source-label">本次取辞 · 传统规则</span>
      <h3>本次为什么看这些内容</h3>
      <p>{{ reading.plain_rule_explanation }}</p>
    </div>

    <div class="traditional-reading__passage-heading">
      <h4>本地典籍资料</h4>
      <span>原文与出处来自本机核验数据</span>
    </div>
    <div class="traditional-reading__passages">
      <section v-for="(passage, index) in reading.passages" :key="`${passage.hexagram_order}-${passage.kind}-${passage.line_position ?? 'gua'}-${index}`" class="traditional-reading__passage">
        <div class="traditional-reading__label">
          <strong>{{ passage.label }}</strong>
          <span v-if="passage.primary" class="traditional-reading__badge">主参考</span>
          <span>{{ passage.hexagram_title }}</span>
        </div>
        <blockquote class="reading-quote"><p>{{ passage.text }}</p></blockquote>
        <a class="source-link" :href="passage.source_url" target="_blank" rel="noreferrer">
          经文来源修订 {{ passage.source_revision_id ?? '旧记录未记录' }}
        </a>
      </section>
    </div>

    <p class="traditional-reading__limit">{{ reading.interpretation_limit }}</p>
    <details class="traditional-reading__metadata">
      <summary>规则版本与出处</summary>
      <div>
        <span>{{ reading.ruleset_name }} · {{ reading.ruleset_version }}</span>
        <a class="source-link" :href="reading.source_url" target="_blank" rel="noreferrer">
          {{ reading.source_title }}（修订 {{ reading.source_revision_id }}）
        </a>
      </div>
    </details>
  </article>
</template>
