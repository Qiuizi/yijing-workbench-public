import { computed, onScopeDispose, ref, watch } from 'vue'
import type { HistoryAIFilter, HistoryList, HistoryQuery, HistorySummary } from './types'

/** Page-local state retained while a record is open, without a global store. */
export function useHistoryList(fetchPage: (query: HistoryQuery) => Promise<HistoryList>) {
  const search = ref('')
  const aiFilter = ref<HistoryAIFilter>('all')
  const page = ref(1)
  const pageSize = 20
  const records = ref<HistorySummary[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref('')
  const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
  let revision = 0
  let timer: ReturnType<typeof setTimeout> | undefined

  async function refresh(targetPage = page.value) {
    clearTimeout(timer)
    const request = ++revision
    const query = { q: search.value.trim(), ai_filter: aiFilter.value, limit: pageSize }
    let requestedPage = Math.max(1, Math.trunc(targetPage))
    loading.value = true
    error.value = ''
    try {
      let response = await fetchPage({ ...query, offset: (requestedPage - 1) * pageSize })
      if (request !== revision) return
      const lastPage = Math.max(1, Math.ceil(response.total / pageSize))
      if (requestedPage > lastPage) {
        requestedPage = lastPage
        response = await fetchPage({ ...query, offset: (requestedPage - 1) * pageSize })
        if (request !== revision) return
      }
      records.value = response.items
      total.value = response.total
      page.value = requestedPage
    } catch (cause) {
      if (request === revision) {
        records.value = []
        error.value = cause instanceof Error ? cause.message : '读取历史记录失败。'
      }
    } finally {
      if (request === revision) loading.value = false
    }
  }

  watch([search, aiFilter], ([, filter], [, previousFilter]) => {
    ++revision // Invalidate results immediately, including during search debounce.
    clearTimeout(timer)
    page.value = 1
    records.value = []
    loading.value = true
    error.value = ''
    if (filter !== previousFilter) void refresh(1)
    else timer = setTimeout(() => { void refresh(1) }, 250)
  }, { flush: 'sync' })

  function goToPage(target: number) {
    if (!loading.value) return refresh(Math.max(1, Math.min(pageCount.value, target)))
  }

  onScopeDispose(() => { ++revision; clearTimeout(timer) })
  return { search, aiFilter, page, pageSize, records, total, loading, error, pageCount, refresh, goToPage }
}
