<script setup lang="ts">
import { computed } from 'vue'
import { Clock, Reading } from '@element-plus/icons-vue'
import type { HistoryAIFilter, HistorySummary } from '../types'

const props = defineProps<{ records: HistorySummary[]; total: number; page: number; pageSize: number; loading: boolean; error: string; openingRecordId?: number | null }>()
const emit = defineEmits<{ open: [id: number]; remove: [record: HistorySummary]; startCasting: []; page: [page: number]; retry: [] }>()
const search = defineModel<string>('search', { required: true })
const aiFilter = defineModel<HistoryAIFilter>('aiFilter', { required: true })
const filterOptions = [
  { id: 'all', label: '全部' },
  { id: 'with-ai', label: '有 AI 解读' },
  { id: 'without-ai', label: '无 AI 解读' },
] as const
const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const hasFilters = computed(() => Boolean(search.value.trim()) || aiFilter.value !== 'all')

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}
</script>

<template>
  <section class="page-panel panel history-page" aria-label="历史记录">
    <div class="section-heading">
      <div><span class="section-index">05</span><h2>历史记录</h2></div>
      <span class="process-caption" aria-live="polite">{{ loading ? '读取中…' : error ? '读取失败' : `本页 ${records.length} 条 / 共 ${total} 条` }} · 排盘上下文随记录恢复</span>
    </div>
    <div class="history-toolbar">
      <el-input v-model="search" :maxlength="500" clearable aria-label="按占问内容搜索历史" placeholder="搜索占问内容…" />
      <div class="history-filter" role="group" aria-label="按 AI 会话筛选">
        <button v-for="filter in filterOptions" :key="filter.id" type="button" :aria-pressed="aiFilter === filter.id" @click="aiFilter = filter.id">{{ filter.label }}</button>
      </div>
    </div>
    <div v-loading="loading" class="history-page__list">
      <div v-if="!loading && error" class="history-empty history-empty--page" role="alert">
        <p>{{ error }}</p><el-button plain @click="emit('retry')">重试</el-button>
      </div>
      <div v-else-if="!loading && !records.length && !hasFilters" class="history-empty history-empty--page">
        <el-icon><Clock /></el-icon><p>还没有起卦记录</p><small>完成一次起卦后，记录会保存在本机。</small>
        <el-button type="primary" @click="emit('startCasting')">开始第一次起卦</el-button>
      </div>
      <div v-else-if="!loading && !records.length" class="history-empty history-empty--page">
        <el-icon><Clock /></el-icon><p>没有符合条件的记录</p><small>试试其他关键词或筛选条件。</small>
        <el-button plain @click="search = ''; aiFilter = 'all'">清除筛选</el-button>
      </div>
      <article v-for="record in records" :key="record.id" class="history-page__item">
        <button class="history-page__open" type="button" :disabled="loading || openingRecordId != null" @click="emit('open', record.id)">
          <span class="history-item__date">{{ formatDate(record.created_at) }} · {{ record.method === 'coins' ? '铜钱起卦' : '手动起卦' }}</span>
          <strong>{{ record.question }}</strong>
          <span class="history-item__hexagrams">{{ record.base_name }}<i>→</i>{{ record.changed_name }}</span>
          <span class="history-item__moving">{{ record.moving_positions.length ? `动爻 ${record.moving_positions.join('、')}` : '本卦无动爻' }} · {{ record.has_ai_sessions ? '有 AI 解读' : '无 AI 解读' }}</span>
        </button>
        <div class="history-page__actions">
          <el-button plain size="small" :loading="openingRecordId === record.id" :disabled="loading || openingRecordId != null" @click="emit('open', record.id)"><el-icon><Reading /></el-icon>打开</el-button>
          <details class="history-more"><summary :aria-label="`记录操作：${record.question}`">⋯</summary><div><button type="button" :disabled="loading" @click="emit('remove', record)">删除记录</button></div></details>
        </div>
      </article>
    </div>
    <nav class="history-pagination" aria-label="历史记录分页">
      <el-button plain :disabled="loading || page <= 1" @click="emit('page', page - 1)">上一页</el-button>
      <span aria-live="polite">第 {{ page }} / {{ pageCount }} 页</span>
      <el-button plain :disabled="loading || page >= pageCount" @click="emit('page', page + 1)">下一页</el-button>
    </nav>
  </section>
</template>
