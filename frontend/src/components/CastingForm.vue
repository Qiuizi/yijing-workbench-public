<script setup lang="ts">
import { computed } from 'vue'
import { Coin, EditPen, Reading } from '@element-plus/icons-vue'
defineProps<{ busy: boolean }>()
const emit = defineEmits<{ cast: []; learn: [] }>()
const question = defineModel<string>('question', { required: true })
const mode = defineModel<'coins' | 'manual'>('mode', { required: true })
const manualLines = defineModel<number[]>('manualLines', { required: true })
const lineNames = ['初爻', '二爻', '三爻', '四爻', '五爻', '上爻']
const manualRows = computed(() =>
  [5, 4, 3, 2, 1, 0].map((index) => ({
    index,
    position: index + 1,
    label: lineNames[index],
  })),
)
</script>
<template>
  <section class="casting-start">
    <header class="casting-start__heading">
      <span class="casting-mark" aria-hidden="true">☰</span>
      <h1>起一卦，整理当下的思路</h1>
      <p>原文与取辞来自本地典籍，结果保存在本机。</p>
    </header>
    <div class="control-panel panel">
      <el-form @submit.prevent="emit('cast')">
        <label class="field-label" for="question">今天你想探讨什么？</label>
        <el-input
          id="question"
          v-model="question"
          type="textarea"
          :rows="4"
          maxlength="500"
          show-word-limit
          placeholder="输入一件具体想思考的事……"
          resize="none"
        />
        <div class="field-hint">问题会随卦象保存在本机历史记录中。</div>

        <label class="field-label mode-label">起卦方式</label>
        <el-radio-group v-model="mode" class="mode-switch">
          <el-radio-button value="coins"
            ><el-icon><Coin /></el-icon> 铜钱起卦</el-radio-button
          >
          <el-radio-button value="manual"
            ><el-icon><EditPen /></el-icon> 手动输入</el-radio-button
          >
        </el-radio-group>

        <div v-if="mode === 'manual'" class="manual-entry">
          <div class="manual-entry__intro">
            按画出的卦象，从上爻到初爻录入爻值。
          </div>
          <div v-for="row in manualRows" :key="row.position" class="manual-row">
            <span class="manual-row__name">{{ row.label }}</span>
            <el-select
              v-model="manualLines[row.index]"
              :aria-label="`${row.label}爻值`"
            >
              <el-option :value="6" label="6 · 老阴（动）" />
              <el-option :value="7" label="7 · 少阳" />
              <el-option :value="8" label="8 · 少阴" />
              <el-option :value="9" label="9 · 老阳（动）" />
            </el-select>
            <span class="manual-row__glyph">{{
              manualLines[row.index] === 6 || manualLines[row.index] === 8
                ? '阴'
                : '阳'
            }}</span>
          </div>
        </div>

        <el-button
          type="primary"
          class="cast-button"
          :loading="busy"
          @click="emit('cast')"
        >
          <el-icon v-if="!busy"><Reading /></el-icon>
          {{ busy ? '起卦中…' : '开始起卦' }}
          <span v-if="!busy" class="cast-button__arrow">↗</span>
        </el-button>
        <p class="privacy-line">
          <span class="privacy-dot"></span>本地保存 · 如需 AI，另外手动启用
        </p>
      </el-form>
    </div>
    <button
      type="button"
      class="quiet-button casting-learn"
      @click="emit('learn')"
    >
      去学习六十四卦 →
    </button>
  </section>
</template>
