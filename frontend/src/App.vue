<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, Clock, Coin, Collection, Compass, Document, EditPen, Expand, Fold, Menu, Operation, Reading, Setting } from '@element-plus/icons-vue'
import HexagramCard from './components/HexagramCard.vue'
import NajiaPanel from './components/NajiaPanel.vue'
import AIPage from './components/AIPage.vue'
import HistoryPage from './components/HistoryPage.vue'
import ReadingPage from './components/ReadingPage.vue'
import SettingsPage from './components/SettingsPage.vue'
import { api } from './api'
import { isTauri } from '@tauri-apps/api/core'
import { specialLineForCast } from './specialLine'
import type { Divination, HistorySummary, NajiaChart } from './types'
import { divinationMarkdown, markdownFilename } from './markdownExport'
import { saveMarkdown } from './saveMarkdown'
import { useHistoryList } from './historyPresentation'

const question = ref('')
const mode = ref<'coins' | 'manual'>('coins')
const manualLines = ref<number[]>([7, 7, 7, 7, 7, 7])
const result = ref<Divination | null>(null)
const busy = ref(false)
const { search: historySearch, aiFilter: historyAIFilter, page: historyPage, pageSize: historyPageSize,
  records: historyItems, total: historyTotal, loading: historyLoading, error: historyError,
  refresh: loadHistory, goToPage: goToHistoryPage } = useHistoryList(api.history)
const loadingRecordId = ref<number | null>(null)
const activePage = ref<'divination' | 'reading' | 'najia' | 'ai' | 'history' | 'settings'>('divination')
const navCollapsed = ref(false)
const mobileNavOpen = ref(false)
const exporting = ref(false)

function updateSavedChart(recordId: number, chart: NajiaChart) {
  if (result.value?.id === recordId) result.value.najia_chart = chart
}

async function exportMarkdown() {
  if (!result.value || exporting.value) return
  exporting.value = true
  try {
    if (await saveMarkdown(markdownFilename(result.value), divinationMarkdown(result.value))) {
      ElMessage.success(isTauri() ? 'Markdown 已保存。' : 'Markdown 下载已发起。')
    }
  } catch (error) {
    ElMessage.error(`导出 Markdown 失败：${error instanceof Error ? error.message : String(error)}`)
  } finally {
    exporting.value = false
  }
}

const pageItems = [
  { id: 'divination', label: '起卦', icon: Compass },
  { id: 'reading', label: '解卦', icon: Document },
  { id: 'najia', label: '六爻排盘', icon: Operation },
  { id: 'ai', label: 'AI 解读', icon: ChatDotRound },
  { id: 'history', label: '历史记录', icon: Clock },
  { id: 'settings', label: '设置', icon: Setting },
] as const

const lineNames = ['初爻', '二爻', '三爻', '四爻', '五爻', '上爻']
const manualRows = computed(() => [5, 4, 3, 2, 1, 0].map((index) => ({
  index,
  position: index + 1,
  label: lineNames[index],
})))
const movingLineText = computed(() => {
  if (!result.value) return []
  return result.value.moving_positions.map((position) => ({
    position,
    label: lineNames[position - 1],
    text: result.value!.base_hexagram.line_texts[position - 1],
  }))
})
const specialLineText = computed(() => result.value
  ? specialLineForCast(result.value.base_hexagram, result.value.lines)
  : null)

async function startDivination() {
  if (!question.value.trim()) {
    ElMessage.warning('先写下要占问的问题。')
    return
  }
  busy.value = true
  try {
    result.value = mode.value === 'coins'
      ? await api.cast(question.value.trim())
      : await api.castManual(question.value.trim(), [...manualLines.value])
    ElMessage.success('起卦完成，已保存到历史记录。')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '起卦失败，请稍后重试。')
  } finally {
    busy.value = false
  }
}

async function selectPage(page: typeof activePage.value) {
  activePage.value = page
  mobileNavOpen.value = false
  if (page === 'history') await loadHistory()
  if (page === 'divination') {
    try {
      mode.value = (await api.preferences()).default_method
    } catch {
      // Casting stays available if a legacy backend does not expose preferences.
    }
  }
}

async function openRecord(id: number) {
  loadingRecordId.value = id
  try {
    result.value = await api.historyItem(id)
    activePage.value = 'divination'
    mobileNavOpen.value = false
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取这条记录失败。')
  } finally {
    loadingRecordId.value = null
  }
}

async function removeRecord(record: HistorySummary) {
  try {
    await ElMessageBox.confirm(`删除“${record.question}”这条起卦记录？`, '删除历史记录', {
      confirmButtonText: '删除',
      cancelButtonText: '保留',
      type: 'warning',
    })
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
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

function valueDescription(value: number) {
  return ({ 6: '老阴', 7: '少阳', 8: '少阴', 9: '老阳' } as Record<number, string>)[value]
}

onMounted(async () => {
  if (isTauri()) {
    try {
      await api.health()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '桌面后端启动失败，请查看 yijing-backend.log。')
    }
  }
  await selectPage('divination')
})
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--nav-collapsed': navCollapsed, 'app-shell--mobile-nav-open': mobileNavOpen }">
    <aside class="app-sidebar" aria-label="主导航">
      <div class="sidebar-brand-row">
        <a class="brand" href="#top" aria-label="易经起卦工作台首页" @click="selectPage('divination')">
          <span class="brand__seal">易</span>
          <span class="brand__wordmark"><strong>易经</strong><small>起卦工作台</small></span>
        </a>
        <button class="sidebar-collapse" type="button" :aria-label="navCollapsed ? '展开导航' : '收起导航'" :title="navCollapsed ? '展开导航' : '收起导航'" @click="navCollapsed = !navCollapsed">
          <el-icon><component :is="navCollapsed ? Expand : Fold" /></el-icon>
        </button>
      </div>
      <nav class="side-nav" aria-label="功能导航">
        <button v-for="page in pageItems" :key="page.id" type="button" class="side-nav__item" :class="{ 'side-nav__item--active': activePage === page.id }" :aria-current="activePage === page.id ? 'page' : undefined" :title="page.label" @click="selectPage(page.id)">
          <el-icon><component :is="page.icon" /></el-icon>
          <span>{{ page.label }}</span>
        </button>
      </nav>
      <div class="sidebar-footnote"><span class="sidebar-footnote__dot"></span><span>本地运行 · 数据保存在此设备</span></div>
    </aside>
    <button v-if="mobileNavOpen" class="mobile-nav-backdrop" type="button" aria-label="关闭导航" @click="mobileNavOpen = false"></button>
    <div class="app-main">
    <header class="topbar">
      <button class="mobile-nav-toggle" type="button" aria-label="打开功能导航" :aria-expanded="mobileNavOpen" @click="mobileNavOpen = !mobileNavOpen">
        <el-icon><Menu /></el-icon>
      </button>
      <span class="topbar__section">本地工作台</span>
      <div class="topbar__right">
        <el-button v-if="result && ['divination', 'reading', 'najia'].includes(activePage)" plain size="small" :loading="exporting" @click="exportMarkdown">导出 Markdown</el-button>
        <span class="edition-note">V3.2.2 · 桌面稳定核心 V3.1.4</span>
      </div>
    </header>

    <main id="top" class="workbench">
      <div v-if="activePage === 'divination'">
      <section class="intro-row" aria-label="工作台介绍">
        <div>
          <p class="overline">ZHOUYI · DIVINATION DESK</p>
          <h1>你想问什么？</h1>
          <p class="intro-copy">写下此刻的问题，用一卦整理思路。卦辞与爻辞按原文呈现。</p>
        </div>
        <div class="intro-stamp" aria-hidden="true"><span>易</span><small>观变</small></div>
      </section>

      <div class="workspace-grid" :class="{ 'workspace-grid--empty': !result }">
        <aside class="control-panel panel" aria-label="起卦操作">
          <div class="section-heading">
            <div><span class="section-index">01</span><h2>起一卦</h2></div>
            <el-icon class="heading-icon"><EditPen /></el-icon>
          </div>

          <el-form @submit.prevent="startDivination">
            <label class="field-label" for="question">占问内容</label>
            <el-input
              id="question"
              v-model="question"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
              placeholder="把问题写具体一些，例如：这次转岗机会，我该如何权衡？"
              resize="none"
            />
            <div class="field-hint">问题会随卦象保存在本机历史记录中。</div>

            <label class="field-label mode-label">起卦方式</label>
            <el-radio-group v-model="mode" class="mode-switch">
              <el-radio-button value="coins"><el-icon><Coin /></el-icon> 铜钱起卦</el-radio-button>
              <el-radio-button value="manual"><el-icon><EditPen /></el-icon> 手动输入</el-radio-button>
            </el-radio-group>

            <div v-if="mode === 'coins'" class="method-note">
              <div class="method-note__coin">☯</div>
              <div><strong>三枚铜钱 · 六次成爻</strong><p>每次掷出阴面 2 或阳面 3，从初爻起，自下而上。</p></div>
            </div>

            <div v-else class="manual-entry">
              <div class="manual-entry__intro">按画出的卦象，从上爻到初爻录入爻值。</div>
              <div v-for="row in manualRows" :key="row.position" class="manual-row">
                <span class="manual-row__name">{{ row.label }}</span>
                <el-select v-model="manualLines[row.index]" :aria-label="`${row.label}爻值`">
                  <el-option :value="6" label="6 · 老阴（动）" />
                  <el-option :value="7" label="7 · 少阳" />
                  <el-option :value="8" label="8 · 少阴" />
                  <el-option :value="9" label="9 · 老阳（动）" />
                </el-select>
                <span class="manual-row__glyph">{{ manualLines[row.index] === 6 || manualLines[row.index] === 8 ? '阴' : '阳' }}</span>
              </div>
            </div>

            <el-button type="primary" class="cast-button" :loading="busy" @click="startDivination">
              <el-icon v-if="!busy"><Reading /></el-icon>
              {{ busy ? '起卦中…' : '开始起卦' }}
              <span v-if="!busy" class="cast-button__arrow">↗</span>
            </el-button>
            <p class="privacy-line"><span class="privacy-dot"></span>记录保存在本机；启用 AI 后会按提示连接 DeepSeek</p>
          </el-form>
        </aside>

        <section class="center-column" aria-label="卦象展示">
          <div class="panel diagram-panel">
            <div class="section-heading section-heading--compact">
              <div><span class="section-index">02</span><h2>卦象</h2></div>
              <span v-if="result" class="result-date">{{ formatDate(result.created_at ?? '') }}</span>
            </div>

            <div v-if="result" class="question-ribbon">
              <span class="question-ribbon__label">所问</span>
              <p>{{ result.question }}</p>
            </div>

            <div v-if="result" class="hexagram-pair">
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
            <div v-else class="empty-diagram">
              <div class="empty-diagram__seal">卦</div>
              <p class="empty-diagram__title">静候一卦</p>
              <p>写下所问，选择起卦方式，<br />卦象会在这里展开。</p>
              <div class="empty-diagram__lines" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></div>
            </div>

            <div v-if="result" class="movement-summary">
              <span class="movement-summary__label">动爻</span>
              <template v-if="result.moving_positions.length">
                <span v-for="position in result.moving_positions" :key="position" class="movement-chip">{{ lineNames[position - 1] }}</span>
              </template>
              <span v-else class="movement-summary__none">本卦无动爻</span>
              <span class="movement-summary__method">{{ result.method === 'coins' ? '三钱法' : '手动录入' }}</span>
            </div>
          </div>

          <section v-if="result" class="panel process-panel" aria-label="每一爻的生成过程">
            <div class="section-heading section-heading--compact">
              <div><span class="section-index">03</span><h2>起爻过程</h2></div>
              <span class="process-caption">从下往上 · 初爻至上爻</span>
            </div>
            <div class="process-list">
              <div v-for="line in result.lines" :key="line.position" class="process-row" :class="{ 'process-row--moving': line.changing }">
                <span class="process-row__position">{{ lineNames[line.position - 1] }}</span>
                <span class="process-row__state">{{ valueDescription(line.value) }}<small>{{ line.value }}</small></span>
                <div v-if="line.coins" class="coin-results" :aria-label="`铜钱结果 ${line.coins.join('、')}`">
                  <span v-for="(coin, index) in line.coins" :key="index" class="coin-face" :class="coin === 3 ? 'coin-face--yang' : 'coin-face--yin'">{{ coin === 3 ? '阳' : '阴' }}</span>
                  <span class="coin-results__sum">合 {{ line.value }}</span>
                </div>
                <div v-else class="coin-results coin-results--manual"><span>手动录入</span><span class="coin-results__sum">{{ line.yin_yang }}爻</span></div>
                <span class="process-row__change">{{ line.changing ? '动' : '' }}</span>
              </div>
            </div>
            <div class="calculation-note"><span>計</span><p>阴爻记为 0，阳爻记为 1；初爻对应最低位。老阴、老阳翻转后查得之卦。</p></div>
          </section>
        </section>

        <aside v-if="result" class="text-column" aria-label="卦象资料">
          <div class="section-heading section-heading--aside">
            <div><span class="section-index">04</span><h2>原文与说明</h2></div>
            <el-icon class="heading-icon"><Collection /></el-icon>
          </div>
          <template v-if="result">
            <article class="text-card panel">
              <div class="text-card__topline"><span class="text-card__eyebrow">本卦 · 第{{ result.base_hexagram.wenwang_order }}卦</span><span class="text-card__seal">辞</span></div>
              <h3>{{ result.base_hexagram.title }}</h3>
              <p class="original-text">{{ result.base_hexagram.judgment }}</p>
              <div class="text-divider"><span>动爻爻辞</span><i></i></div>
              <div v-if="movingLineText.length" class="line-text-list">
                <div v-for="line in movingLineText" :key="line.position" class="line-text-item">
                  <span>{{ line.label }}</span><p>{{ line.text }}</p>
                </div>
              </div>
              <p v-else class="quiet-note">本卦无动爻，此处不列爻辞。</p>
              <div v-if="specialLineText" class="special-line-text" aria-label="特殊爻辞">
                <span>{{ specialLineText.name }}</span><p>{{ specialLineText.text }}</p>
              </div>
              <a class="source-link" :href="result.base_hexagram.source_url" target="_blank" rel="noreferrer">文本来源：维基文库<el-icon><Reading /></el-icon></a>
            </article>

            <article class="text-card panel changed-text-card">
              <div class="text-card__topline"><span class="text-card__eyebrow">之卦 · 第{{ result.changed_hexagram.wenwang_order }}卦</span><span class="text-card__seal">变</span></div>
              <h3>{{ result.changed_hexagram.title }}</h3>
              <p class="original-text">{{ result.changed_hexagram.judgment }}</p>
              <p class="quiet-note changed-text-card__note">变卦卦辞供对照；本应用仅展示原文与爻象，不推演额外断语。</p>
              <a class="source-link" :href="result.changed_hexagram.source_url" target="_blank" rel="noreferrer">文本来源：维基文库<el-icon><Reading /></el-icon></a>
            </article>

          </template>
          <div v-if="result" class="source-footnote">
            <span class="source-footnote__mark">注</span>
            <p>经文按维基文库逐卦原文页转录，字形与标点依页面版本。不同传本或有异文。</p>
          </div>
        </aside>
      </div>

      </div>
      <ReadingPage v-else-if="activePage === 'reading'" :divination="result" @start-casting="selectPage('divination')" />
      <NajiaPanel v-else-if="activePage === 'najia'" :divination="result" @chart-updated="updateSavedChart" @start-casting="selectPage('divination')" />
      <AIPage v-else-if="activePage === 'ai'" :divination="result" @start-casting="selectPage('divination')" />
      <HistoryPage v-else-if="activePage === 'history'" v-model:search="historySearch" v-model:ai-filter="historyAIFilter"
        :records="historyItems" :total="historyTotal" :page="historyPage" :page-size="historyPageSize" :error="historyError"
        :loading="historyLoading" :opening-record-id="loadingRecordId" @page="goToHistoryPage" @retry="loadHistory()"
        @open="openRecord" @remove="removeRecord" @start-casting="selectPage('divination')" />
      <SettingsPage v-else />
    </main>

    <footer class="app-footer">
      <span>本地工作台</span><i></i><span>卦序采用文王序</span><i></i><span>数据保存在此设备</span>
    </footer>
    </div>
  </div>
</template>
