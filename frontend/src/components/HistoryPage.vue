<script setup lang="ts">
import { computed, ref } from 'vue'
import { Clock, Delete, Reading } from '@element-plus/icons-vue'
import { filterHistoryRecords, type HistoryAIFilter } from '../historyPresentation'
import type { HistorySummary } from '../types'

const props = defineProps<{ records: HistorySummary[]; loading: boolean; openingRecordId?: number | null }>()
const emit = defineEmits<{ open: [id: number]; remove: [record: HistorySummary]; startCasting: [] }>()
const search = ref('')
const aiFilter = ref<HistoryAIFilter>('all')
const filterOptions = [
  { id: 'all', label: '全部' },
  { id: 'with-ai', label: '有 AI 解读' },
  { id: 'without-ai', label: '无 AI 解读' },
] as const
const filteredRecords = computed(() => filterHistoryRecords(props.records, search.value, aiFilter.value))

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}
</script>

<template>
  <section class="page-panel panel history-page" aria-label="历史记录">
    <div class="section-heading">
      <div><span class="section-index">05</span><h2>历史记录</h2></div>
      <span class="process-caption">{{ filteredRecords.length }} / {{ records.length }} 条 · 排盘上下文随记录恢复</span>
    </div>
    <div class="history-toolbar">
      <el-input v-model="search" clearable aria-label="按占问内容搜索历史" placeholder="搜索占问内容…" />
      <div class="history-filter" role="group" aria-label="按 AI 会话筛选">
        <button v-for="filter in filterOptions" :key="filter.id" type="button" :aria-pressed="aiFilter === filter.id" @click="aiFilter = filter.id">{{ filter.label }}</button>
      </div>
    </div>
    <div v-loading="loading" class="history-page__list">
      <div v-if="!loading && !records.length" class="history-empty history-empty--page">
        <el-icon><Clock /></el-icon><p>还没有起卦记录</p><small>完成一次起卦后，记录会保存在本机。</small>
        <el-button type="primary" @click="emit('startCasting')">开始第一次起卦</el-button>
      </div>
      <div v-else-if="!loading && !filteredRecords.length" class="history-empty history-empty--page">
        <el-icon><Clock /></el-icon><p>没有符合条件的记录</p><small>试试其他关键词或筛选条件。</small>
        <el-button plain @click="search = ''; aiFilter = 'all'">清除筛选</el-button>
      </div>
      <article v-for="record in filteredRecords" :key="record.id" class="history-page__item">
        <button class="history-page__open" type="button" @click="emit('open', record.id)">
          <span class="history-item__date">{{ formatDate(record.created_at) }} · {{ record.method === 'coins' ? '铜钱起卦' : '手动起卦' }}</span>
          <strong>{{ record.question }}</strong>
          <span class="history-item__hexagrams">{{ record.base_name }}<i>→</i>{{ record.changed_name }}</span>
          <span class="history-item__moving">{{ record.moving_positions.length ? `动爻 ${record.moving_positions.join('、')}` : '本卦无动爻' }} · {{ record.has_ai_sessions ? '有 AI 解读' : '无 AI 解读' }}</span>
        </button>
        <div class="history-page__actions">
          <el-button plain size="small" :loading="openingRecordId === record.id" :disabled="openingRecordId !== null && openingRecordId !== undefined" @click="emit('open', record.id)"><el-icon><Reading /></el-icon>打开</el-button>
          <el-button text circle aria-label="删除记录" @click="emit('remove', record)"><el-icon><Delete /></el-icon></el-button>
        </div>
      </article>
    </div>
  </section>
</template>
