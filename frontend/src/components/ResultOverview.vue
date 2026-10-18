<script setup lang="ts">
import { computed } from 'vue'
import { Collection, Reading } from '@element-plus/icons-vue'
import HexagramCard from './HexagramCard.vue'
import { specialLineForCast } from '../specialLine'
import type { Divination } from '../types'
const props = defineProps<{ result: Divination }>()
const emit = defineEmits<{ read: []; learn: [id: number] }>()
const lineNames = ['初爻', '二爻', '三爻', '四爻', '五爻', '上爻']
const movingLineText = computed(() =>
  props.result.moving_positions.map((position) => ({
    position,
    label: lineNames[position - 1],
    text: props.result.base_hexagram.line_texts[position - 1],
  })),
)
const specialLineText = computed(() =>
  specialLineForCast(props.result.base_hexagram, props.result.lines),
)
function valueDescription(value: number) {
  return (
    { 6: '老阴', 7: '少阳', 8: '少阴', 9: '老阳' } as Record<number, string>
  )[value]
}
</script>
<template>
  <div class="result-overview">
    <div class="panel diagram-panel">
      <div class="hexagram-pair">
        <HexagramCard
          :hexagram="result.base_hexagram"
          :lines="result.lines"
          :moving-positions="result.moving_positions"
        />
        <div class="change-connector" aria-label="变化为">
          <span>變</span><i></i>
        </div>
        <HexagramCard
          :hexagram="result.changed_hexagram"
          :lines="result.changed_lines"
          :moving-positions="result.moving_positions"
          changed
        />
      </div>
      <div class="movement-summary">
        <span class="movement-summary__label">动爻</span>
        <template v-if="result.moving_positions.length">
          <span
            v-for="position in result.moving_positions"
            :key="position"
            class="movement-chip"
            >{{ lineNames[position - 1] }}</span
          >
        </template>
        <span v-else class="movement-summary__none">本卦无动爻</span>
        <span class="movement-summary__method">{{
          result.method === 'coins' ? '三钱法' : '手动录入'
        }}</span>
      </div>
    </div>

    <aside class="text-column" aria-label="卦象资料">
      <div class="section-heading section-heading--aside">
        <div>
          <span class="section-index">04</span>
          <h2>原文与说明</h2>
        </div>
        <el-icon class="heading-icon"><Collection /></el-icon>
      </div>
      <article class="text-card panel">
        <div class="text-card__topline">
          <span class="text-card__eyebrow"
            >本卦 · 第{{ result.base_hexagram.wenwang_order }}卦</span
          ><span class="text-card__seal">辞</span>
        </div>
        <h3>{{ result.base_hexagram.title }}</h3>
        <p class="original-text">{{ result.base_hexagram.judgment }}</p>
        <div class="text-divider"><span>动爻爻辞</span><i></i></div>
        <div v-if="movingLineText.length" class="line-text-list">
          <div
            v-for="line in movingLineText"
            :key="line.position"
            class="line-text-item"
          >
            <span>{{ line.label }}</span>
            <p>{{ line.text }}</p>
          </div>
        </div>
        <p v-else class="quiet-note">本卦无动爻，此处不列爻辞。</p>
        <div
          v-if="specialLineText"
          class="special-line-text"
          aria-label="特殊爻辞"
        >
          <span>{{ specialLineText.name }}</span>
          <p>{{ specialLineText.text }}</p>
        </div>
        <a
          class="source-link"
          :href="result.base_hexagram.source_url"
          target="_blank"
          rel="noreferrer"
          >文本来源：维基文库<el-icon><Reading /></el-icon
        ></a>
      </article>

      <article class="text-card panel changed-text-card">
        <div class="text-card__topline">
          <span class="text-card__eyebrow"
            >之卦 · 第{{ result.changed_hexagram.wenwang_order }}卦</span
          ><span class="text-card__seal">变</span>
        </div>
        <h3>{{ result.changed_hexagram.title }}</h3>
        <p class="original-text">{{ result.changed_hexagram.judgment }}</p>
        <p class="quiet-note changed-text-card__note">
          变卦卦辞供对照；本应用仅展示原文与爻象，不推演额外断语。
        </p>
        <a
          class="source-link"
          :href="result.changed_hexagram.source_url"
          target="_blank"
          rel="noreferrer"
          >文本来源：维基文库<el-icon><Reading /></el-icon
        ></a>
      </article>

      <div class="source-footnote">
        <span class="source-footnote__mark">注</span>
        <p>
          经文按维基文库逐卦原文页转录，字形与标点依页面版本。不同传本或有异文。
        </p>
      </div>
    </aside>
    <details class="panel process-panel" aria-label="每一爻的生成过程">
      <summary>详细起爻过程 <span>展开 / 收起</span></summary>
      <div class="section-heading section-heading--compact">
        <div>
          <span class="section-index">03</span>
          <h2>起爻过程</h2>
        </div>
        <span class="process-caption">从下往上 · 初爻至上爻</span>
      </div>
      <div class="process-list">
        <div
          v-for="line in result.lines"
          :key="line.position"
          class="process-row"
          :class="{ 'process-row--moving': line.changing }"
        >
          <span class="process-row__position">{{
            lineNames[line.position - 1]
          }}</span>
          <span class="process-row__state"
            >{{ valueDescription(line.value)
            }}<small>{{ line.value }}</small></span
          >
          <div
            v-if="line.coins"
            class="coin-results"
            :aria-label="`铜钱结果 ${line.coins.join('、')}`"
          >
            <span
              v-for="(coin, index) in line.coins"
              :key="index"
              class="coin-face"
              :class="coin === 3 ? 'coin-face--yang' : 'coin-face--yin'"
              >{{ coin === 3 ? '阳' : '阴' }}</span
            >
            <span class="coin-results__sum">合 {{ line.value }}</span>
          </div>
          <div v-else class="coin-results coin-results--manual">
            <span>手动录入</span
            ><span class="coin-results__sum">{{ line.yin_yang }}爻</span>
          </div>
          <span class="process-row__change">{{
            line.changing ? '动' : ''
          }}</span>
        </div>
      </div>
      <div class="calculation-note">
        <span>計</span>
        <p>
          阴爻记为 0，阳爻记为 1；初爻对应最低位。老阴、老阳翻转后查得之卦。
        </p>
      </div>
    </details>
    <div class="result-read-actions">
      <button type="button" class="quiet-button" @click="emit('read')">
        查看经典与取辞 →</button
      ><button
        type="button"
        class="quiet-button"
        @click="emit('learn', result.base_hexagram.wenwang_order)"
      >
        阅读本卦完整原文 →
      </button>
    </div>
  </div>
</template>
