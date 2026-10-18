<script setup lang="ts">
import { computed, nextTick, onScopeDispose, ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { api } from '../api'
import { filterHexagrams, reviewedGuide, type LearningGroup } from '../learning'
import { createHexagramCache, useLearningResource } from '../learningResource'
import type { HexagramSummary } from '../types'
import HexagramGlyph from './HexagramGlyph.vue'
import LearningPreview from './LearningPreview.vue'
import LearningReader from './LearningReader.vue'

const props = defineProps<{ visible: boolean; hexagramId: number | null }>()
const emit = defineEmits<{ open: [id: number]; back: [] }>()
const entries = ref<HexagramSummary[]>([])
const search = ref('')
const group = ref<LearningGroup>('all')
const selectedId = ref(3)
const listLoading = ref(false)
const listError = ref('')
const gallery = ref<HTMLElement | null>(null)
const indexScroll = ref<HTMLElement | null>(null)
const reader = ref<{ focusHeading: () => void } | null>(null)
const getHexagram = createHexagramCache(api.hexagram)
const {
  entry: detail,
  loading: detailLoading,
  error: detailError,
  read: readDetail,
  reset: resetDetail,
} = useLearningResource(getHexagram)
const {
  entry: preview,
  loading: previewLoading,
  error: previewError,
  read: readPreview,
  reset: resetPreview,
} = useLearningResource(getHexagram)
const filtered = computed(() =>
  filterHexagrams(entries.value, search.value, group.value),
)
const selectedEntry = computed(
  () =>
    filtered.value.find((entry) => entry.wenwang_order === selectedId.value) ??
    null,
)
const guide = computed(() =>
  detail.value ? reviewedGuide(detail.value.wenwang_order) : undefined,
)
const groups = [
  { id: 'all', label: '全部 64' },
  { id: 'upper', label: '上经 30' },
  { id: 'lower', label: '下经 34' },
] as const
let routeRequest = 0
let scrollPosition = 0
let indexScrollPosition = 0
let focusedCard: number | null = null

function restoreGallery() {
  if (!props.visible || props.hexagramId) return
  if (indexScroll.value) indexScroll.value.scrollTop = indexScrollPosition
  if (focusedCard)
    gallery.value
      ?.querySelector<HTMLElement>(`[data-hexagram="${focusedCard}"]`)
      ?.focus({ preventScroll: true })
  window.scrollTo(0, scrollPosition)
}
function onRouteEntered() {
  if (!props.visible) return
  if (props.hexagramId) reader.value?.focusHeading()
  else restoreGallery()
}
function open(id: number) {
  scrollPosition = window.scrollY
  indexScrollPosition = indexScroll.value?.scrollTop ?? 0
  focusedCard = id
  selectedId.value = id
  emit('open', id)
}
async function activate() {
  const request = ++routeRequest
  if (!props.visible) {
    resetDetail()
    resetPreview()
    listLoading.value = false
    return
  }
  if (props.hexagramId) {
    resetPreview()
    await readDetail(props.hexagramId)
    if (request !== routeRequest) return
    await nextTick()
    window.scrollTo(0, 0)
    reader.value?.focusHeading()
    return
  }
  resetDetail()
  listError.value = ''
  listLoading.value = !entries.value.length
  try {
    if (!entries.value.length) {
      const response = await api.hexagrams()
      if (request !== routeRequest) return
      entries.value = response
    }
  } catch (reason) {
    if (request === routeRequest)
      listError.value =
        reason instanceof Error ? reason.message : '资料读取失败，请重试。'
  } finally {
    if (request === routeRequest) {
      listLoading.value = false
      await nextTick()
      restoreGallery()
    }
  }
}
watch(
  () => [props.visible, props.hexagramId],
  () => {
    void activate()
  },
  { immediate: true },
)
watch(filtered, (values) => {
  if (
    values.length &&
    !values.some((entry) => entry.wenwang_order === selectedId.value)
  )
    selectedId.value = values[0]!.wenwang_order
})
watch(
  () => [props.visible, props.hexagramId, selectedEntry.value?.wenwang_order],
  () => {
    if (props.visible && !props.hexagramId && selectedEntry.value)
      void readPreview(selectedEntry.value.wenwang_order)
    else resetPreview()
  },
  { immediate: true },
)
onScopeDispose(() => {
  routeRequest++
})
function retryPreview() {
  if (selectedEntry.value) void readPreview(selectedEntry.value.wenwang_order)
}
function resetFilters() {
  search.value = ''
  group.value = 'all'
}
// Layout changes can fire pointer boundary events under a stationary mouse.
// Only actual pointer movement may replace a keyboard-selected preview.
let pointerX = Number.NaN
let pointerY = Number.NaN
function onIndexPointerMove(event: PointerEvent, id: number) {
  if (event.pointerType !== 'mouse') return
  if (event.clientX !== pointerX || event.clientY !== pointerY) selectedId.value = id
  pointerX = event.clientX
  pointerY = event.clientY
}
function onIndexKeydown(event: KeyboardEvent, index: number) {
  if (event.altKey || event.ctrlKey || event.metaKey || !gallery.value) return
  const columns = getComputedStyle(gallery.value).gridTemplateColumns.split(
    ' ',
  ).length
  const next = (
    {
      ArrowRight: index + 1,
      ArrowLeft: index - 1,
      ArrowDown: index + columns,
      ArrowUp: index - columns,
      Home: 0,
      End: filtered.value.length - 1,
    } as Record<string, number>
  )[event.key]
  if (next === undefined) return
  event.preventDefault()
  const buttons =
    gallery.value.querySelectorAll<HTMLButtonElement>('[data-hexagram]')
  buttons[Math.max(0, Math.min(next, buttons.length - 1))]?.focus()
}
</script>
<template>
  <section class="learning-page" aria-label="六十四卦学习">
    <Transition
      name="learning-route"
      mode="out-in"
      @after-enter="onRouteEntered"
    >
      <div v-if="!hexagramId" key="index" class="learning-index-view">
        <section class="learning-index" :aria-busy="listLoading">
          <header class="learning-index__heading">
            <div>
              <p class="learning-eyebrow">以卦象为索引</p>
              <h1>六十四卦</h1>
            </div>
            <span class="learning-index__hint">选一卦，读原文。</span>
          </header>
          <div class="learning-index__tools">
            <div
              class="learning-index__filter"
              role="group"
              aria-label="经篇筛选"
            >
              <button
                v-for="item in groups"
                :key="item.id"
                type="button"
                :aria-pressed="group === item.id"
                @click="group = item.id"
              >
                {{ item.label }}
              </button>
            </div>
            <el-input
              v-model="search"
              clearable
              :prefix-icon="Search"
              aria-label="搜索卦名或卦序"
              placeholder="搜索卦名、卦序或上下卦"
            />
          </div>
          <div v-if="listError" class="learning-state" role="alert">
            <h2>暂时无法读取典籍</h2>
            <p>{{ listError }}</p>
            <el-button @click="activate">重新读取</el-button>
          </div>
          <div v-else-if="listLoading" class="learning-state" role="status">
            正在读取本地典籍…
          </div>
          <div v-else-if="!filtered.length" class="learning-state">
            <h2>没有找到相符的卦</h2>
            <p>试试卦名、1–64 的序号，或清除筛选。</p>
            <el-button @click="resetFilters">查看全部六十四卦</el-button>
          </div>
          <div v-else ref="indexScroll" class="learning-index__scroll">
            <div
              ref="gallery"
              class="learning-matrix learning-grid"
              role="group"
              aria-label="文王序六十四卦索引"
            >
              <button
                v-for="(entry, index) in filtered"
                :key="entry.wenwang_order"
                type="button"
                class="learning-card learning-matrix__entry"
                :class="{ 'is-selected': selectedId === entry.wenwang_order }"
                :data-hexagram="entry.wenwang_order"
                :aria-current="
                  selectedId === entry.wenwang_order ? 'true' : undefined
                "
                :aria-label="`第${entry.wenwang_order}卦 ${entry.title}，阅读原文`"
                @pointermove="onIndexPointerMove($event, entry.wenwang_order)"
                @focus="selectedId = entry.wenwang_order"
                @keydown="onIndexKeydown($event, index)"
                @click="open(entry.wenwang_order)"
              >
                <span class="learning-matrix__number">{{
                  String(entry.wenwang_order).padStart(2, '0')
                }}</span
                ><HexagramGlyph
                  :code="entry.binary_code"
                  :label="entry.title"
                  compact
                /><strong>{{ entry.title }}</strong
                ><span class="learning-matrix__trigrams"
                  >{{ entry.upper_trigram.name }}上 ·
                  {{ entry.lower_trigram.name }}下</span
                >
              </button>
            </div>
          </div>
          <footer class="learning-index__footer">
            <span aria-live="polite">文王序 · {{ filtered.length }} 卦</span
            ><span>经典原文，本地可读</span>
          </footer>
        </section>
        <aside class="learning-preview-frame" aria-label="当前卦象预览">
          <Transition name="learning-preview" mode="out-in"
            ><LearningPreview
              v-if="selectedEntry"
              :key="selectedEntry.wenwang_order"
              :entry="selectedEntry"
              :hexagram="preview"
              :loading="previewLoading"
              :error="previewError"
              @open="open"
              @retry="retryPreview"
            />
            <div v-else key="none" class="learning-preview-empty">
              <p>从一卦开始</p>
              <span>{{
                listLoading
                  ? '正在读取本地典籍…'
                  : '选择目录中的一卦，查看卦象与原文。'
              }}</span>
            </div></Transition
          >
        </aside>
      </div>
      <div
        v-else
        :key="hexagramId"
        class="learning-reader-view"
        :aria-busy="detailLoading"
      >
        <div v-if="detailError" class="learning-state" role="alert">
          <button
            class="learning-text-button"
            type="button"
            @click="emit('back')"
          >
            ← 返回六十四卦
          </button>
          <h2>暂时无法读取典籍</h2>
          <p>{{ detailError }}</p>
          <el-button @click="activate">重新读取</el-button>
        </div>
        <div v-else-if="detailLoading" class="learning-state" role="status">
          正在翻开这一页…
        </div>
        <LearningReader
          v-else-if="detail"
          ref="reader"
          :hexagram="detail"
          :guide="guide"
          @open="(id) => emit('open', id)"
          @back="emit('back')"
        />
      </div>
    </Transition>
  </section>
</template>
<style src="./LearningPage.css"></style>
