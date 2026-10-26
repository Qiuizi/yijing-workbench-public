<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Clock,
  Compass,
  Expand,
  Fold,
  Moon,
  Reading,
  Setting,
  Sunny,
} from '@element-plus/icons-vue'
import CastingForm from './components/CastingForm.vue'
import ResultOverview from './components/ResultOverview.vue'
import LearningPage from './components/LearningPage.vue'
import LearningHeader from './components/LearningHeader.vue'
import { useNavigation, type Page } from './navigation'
import NajiaPanel from './components/NajiaPanel.vue'
import AIPage from './components/AIPage.vue'
import HistoryPage from './components/HistoryPage.vue'
import ReadingPage from './components/ReadingPage.vue'
import SettingsPage from './components/SettingsPage.vue'
import { api } from './api'
import { isTauri } from '@tauri-apps/api/core'
import type { Divination, HistorySummary, NajiaChart } from './types'
import { divinationMarkdown, markdownFilename } from './markdownExport'
import { saveMarkdown } from './saveMarkdown'
import { useHistoryList } from './historyPresentation'
import { useAppearance } from './appearance'
import BrandMark from './components/BrandMark.vue'

const question = ref('')
const mode = ref<'coins' | 'manual'>('coins')
const manualLines = ref<number[]>([7, 7, 7, 7, 7, 7])
const result = ref<Divination | null>(null)
const busy = ref(false)
const {
  search: historySearch,
  aiFilter: historyAIFilter,
  page: historyPage,
  pageSize: historyPageSize,
  records: historyItems,
  total: historyTotal,
  loading: historyLoading,
  error: historyError,
  refresh: loadHistory,
  goToPage: goToHistoryPage,
} = useHistoryList(api.history)
const loadingRecordId = ref<number | null>(null)
const { route, navigate } = useNavigation()
const activePage = computed(() => route.value.page)
const resultTab = ref('overview')
const resultTabs = [
  { id: 'overview', label: '结果概览' },
  { id: 'reading', label: '经典与取辞' },
  { id: 'najia', label: '六爻排盘' },
  { id: 'ai', label: 'AI 辅助 · 可选联网' },
]
const pageTitle = computed(
  () => pageItems.find((item) => item.id === activePage.value)?.label ?? '起卦',
)
const navCollapsed = ref(false)
const { resolved: appearance, setMode } = useAppearance()
const exporting = ref(false)
// 占问可以写满 500 字，结果页标题需要可折叠，否则卦象会被长文本挤出首屏。
const questionExpanded = ref(false)
const questionIsLong = computed(
  () => (result.value?.question.trim().length ?? 0) > 60,
)

function updateSavedChart(recordId: number, chart: NajiaChart) {
  if (result.value?.id === recordId) result.value.najia_chart = chart
}

async function exportMarkdown() {
  if (!result.value || exporting.value) return
  exporting.value = true
  try {
    if (
      await saveMarkdown(
        markdownFilename(result.value),
        divinationMarkdown(result.value),
      )
    ) {
      ElMessage.success(
        isTauri() ? 'Markdown 已保存。' : 'Markdown 下载已发起。',
      )
    }
  } catch (error) {
    ElMessage.error(
      `导出 Markdown 失败：${error instanceof Error ? error.message : String(error)}`,
    )
  } finally {
    exporting.value = false
  }
}

const pageItems = [
  { id: 'divination', label: '起卦', icon: Compass },
  { id: 'learning', label: '学习', icon: Reading },
  { id: 'history', label: '历史记录', icon: Clock },
  { id: 'settings', label: '设置', icon: Setting },
] as const

async function startDivination() {
  if (busy.value) return
  if (!question.value.trim()) {
    ElMessage.warning('先写下要占问的问题。')
    return
  }
  busy.value = true
  try {
    result.value =
      mode.value === 'coins'
        ? await api.cast(question.value.trim())
        : await api.castManual(question.value.trim(), [...manualLines.value])
    resultTab.value = 'overview'
    questionExpanded.value = false
    ElMessage.success('起卦完成，已保存到历史记录。')
  } catch (error) {
    ElMessage.error(
      error instanceof Error ? error.message : '起卦失败，请稍后重试。',
    )
  } finally {
    busy.value = false
  }
}

function restartCasting() {
  result.value = null
  resultTab.value = 'overview'
  navigate('divination')
}

function selectPage(page: Page) {
  navigate(page)
}
watch(
  activePage,
  async (page) => {
    if (page === 'history') await loadHistory()
    if (page === 'divination') {
      try {
        mode.value = (await api.preferences()).default_method
      } catch {
        /* Keep the current local mode on failure. */
      }
    }
  },
  { immediate: true },
)

async function openRecord(id: number) {
  loadingRecordId.value = id
  try {
    result.value = await api.historyItem(id)
    resultTab.value = 'overview'
    questionExpanded.value = false
    navigate('divination')
  } catch (error) {
    ElMessage.error(
      error instanceof Error ? error.message : '读取这条记录失败。',
    )
  } finally {
    loadingRecordId.value = null
  }
}

async function removeRecord(record: HistorySummary) {
  try {
    await ElMessageBox.confirm(
      `删除“${record.question}”这条起卦记录？`,
      '删除历史记录',
      {
        confirmButtonText: '删除',
        cancelButtonText: '保留',
        type: 'warning',
      },
    )
    await api.deleteHistory(record.id)
    if (result.value?.id === record.id) result.value = null
    await loadHistory()
    ElMessage.success('记录已删除。')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error instanceof Error ? error.message : '删除失败。')
    }
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

onMounted(async () => {
  if (isTauri()) {
    try {
      await api.health()
    } catch (error) {
      ElMessage.error(
        error instanceof Error
          ? error.message
          : '桌面后端启动失败，请查看 yijing-backend.log。',
      )
    }
  }
})
</script>

<template>
  <div
    class="app-shell"
    :class="{
      'app-shell--nav-collapsed': navCollapsed,
      'app-shell--learning': activePage === 'learning',
    }"
  >
    <aside
      v-if="activePage !== 'learning'"
      class="app-sidebar"
      aria-label="主导航"
    >
      <div class="sidebar-brand-row">
        <a
          class="brand"
          href="#/divination"
          @click.prevent="selectPage('divination')"
          aria-label="易经起卦工作台首页"
        >
          <BrandMark :size="34" />
          <span class="brand__wordmark"
            ><strong>易经</strong><small>起卦工作台</small></span
          >
        </a>
        <button
          class="sidebar-collapse"
          type="button"
          :aria-label="navCollapsed ? '展开导航' : '收起导航'"
          :title="navCollapsed ? '展开导航' : '收起导航'"
          @click="navCollapsed = !navCollapsed"
        >
          <el-icon><component :is="navCollapsed ? Expand : Fold" /></el-icon>
        </button>
      </div>
      <nav class="side-nav" aria-label="功能导航">
        <button
          v-for="page in pageItems"
          :key="page.id"
          type="button"
          class="side-nav__item"
          :class="{ 'side-nav__item--active': activePage === page.id }"
          :aria-current="activePage === page.id ? 'page' : undefined"
          :title="page.label"
          @click="selectPage(page.id)"
        >
          <el-icon><component :is="page.icon" /></el-icon>
          <span>{{ page.label }}</span>
        </button>
      </nav>
      <div class="sidebar-footnote">
        <span class="sidebar-footnote__dot"></span
        ><span>本地运行 · 数据保存在此设备</span>
      </div>
    </aside>
    <div class="app-main">
      <LearningHeader v-if="activePage === 'learning'" @navigate="selectPage" />
      <header v-else class="topbar">
        <div class="topbar__lead">
          <BrandMark class="topbar__brand" :size="22" />
          <span class="topbar__section">{{ pageTitle }}</span>
        </div>
        <div class="topbar__right">
          <button
            class="appearance-toggle"
            type="button"
            :aria-label="appearance === 'dark' ? '切换到日间模式' : '切换到夜间模式'"
            :title="appearance === 'dark' ? '切换到日间模式' : '切换到夜间模式'"
            @click="setMode(appearance === 'dark' ? 'light' : 'dark')"
          >
            <el-icon><component :is="appearance === 'dark' ? Sunny : Moon" /></el-icon>
          </button>
          <el-button
            v-if="result && activePage === 'divination'"
            plain
            size="small"
            :loading="exporting"
            @click="exportMarkdown"
            >导出 Markdown</el-button
          >
        </div>
      </header>

      <main id="top" class="workbench">
        <template v-if="activePage === 'divination'">
          <CastingForm
            v-if="!result"
            v-model:question="question"
            v-model:mode="mode"
            v-model:manual-lines="manualLines"
            :busy="busy"
            @cast="startDivination"
            @learn="navigate('learning')"
          />
          <section v-else class="casting-result" aria-label="起卦结果">
            <div class="result-toolbar">
              <button
                type="button"
                class="quiet-button"
                @click="restartCasting"
              >
                ← 再起一卦</button
              ><span
                >当前结果 ·
                {{
                  result.created_at ? formatDate(result.created_at) : ''
                }}</span
              >
            </div>
            <div class="result-heading">
              <span class="page-kicker">观象 · 读辞</span>
              <h1
                :id="'result-question'"
                :class="{ 'result-heading__question--clamped': questionIsLong && !questionExpanded }"
                :title="result.question"
              >
                {{ result.question }}
              </h1>
              <button
                v-if="questionIsLong"
                type="button"
                class="result-heading__toggle"
                :aria-expanded="questionExpanded ? 'true' : 'false'"
                aria-controls="result-question"
                @click="questionExpanded = !questionExpanded"
              >
                {{ questionExpanded ? '收起占问' : '展开完整占问' }}
              </button>
            </div>
            <nav class="result-tabs" aria-label="结果功能">
              <button
                v-for="tab in resultTabs"
                :key="tab.id"
                type="button"
                :aria-current="resultTab === tab.id ? 'page' : undefined"
                @click="resultTab = tab.id"
              >
                {{ tab.label }}
              </button>
            </nav>
            <ResultOverview
              v-if="resultTab === 'overview'"
              :result="result"
              @read="resultTab = 'reading'"
              @learn="(id) => navigate('learning', id)"
            />
            <ReadingPage
              v-else-if="resultTab === 'reading'"
              :divination="result"
              @start-casting="result = null"
            />
            <NajiaPanel
              v-else-if="resultTab === 'najia'"
              :divination="result"
              @chart-updated="updateSavedChart"
              @start-casting="result = null"
            />
            <AIPage
              v-else-if="resultTab === 'ai'"
              :divination="result"
              @start-casting="result = null"
            />
          </section>
        </template>
        <LearningPage
          v-show="activePage === 'learning'"
          :visible="activePage === 'learning'"
          :hexagram-id="route.hexagramId"
          @open="(id) => navigate('learning', id)"
          @back="navigate('learning')"
        />
        <HistoryPage
          v-if="activePage === 'history'"
          v-model:search="historySearch"
          v-model:ai-filter="historyAIFilter"
          :records="historyItems"
          :total="historyTotal"
          :page="historyPage"
          :page-size="historyPageSize"
          :error="historyError"
          :loading="historyLoading"
          :opening-record-id="loadingRecordId"
          @page="goToHistoryPage"
          @retry="loadHistory()"
          @open="openRecord"
          @remove="removeRecord"
          @start-casting="restartCasting"
        />
        <SettingsPage v-if="activePage === 'settings'" />
      </main>
      <footer v-if="activePage !== 'learning'" class="app-footer">
        <span>本地保存</span><i></i><span>经典原文 · 自在探索</span>
      </footer>
    </div>
    <nav
      v-if="activePage !== 'learning'"
      class="bottom-nav"
      aria-label="移动端主导航"
    >
      <button
        v-for="page in pageItems"
        :key="page.id"
        type="button"
        :aria-current="activePage === page.id ? 'page' : undefined"
        @click="selectPage(page.id)"
      >
        <el-icon><component :is="page.icon" /></el-icon
        ><span>{{ page.label }}</span>
      </button>
    </nav>
  </div>
</template>
