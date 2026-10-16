import { effectScope } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useHistoryList } from './historyPresentation'
import { divinationMarkdown } from './markdownExport'
import { api } from './api'
import type { Divination, HistoryList, HistoryQuery, HistorySummary } from './types'

vi.mock('@tauri-apps/api/core', () => ({ isTauri: () => false }))
const scopes: ReturnType<typeof effectScope>[] = []
function useList(loader: (query: HistoryQuery) => Promise<HistoryList>) {
  const scope = effectScope(); scopes.push(scope)
  return scope.run(() => useHistoryList(loader))!
}
function rows(count: number): HistorySummary[] {
  return Array.from({ length: count }, (_, i) => ({ id: count - i, question: `合成占问 ${count - i}`, method: 'manual',
    base_name: '乾', changed_name: '姤', moving_positions: [1], created_at: '2026-10-16T00:00:00Z' }))
}
function deferred() {
  let resolve!: (value: HistoryList) => void
  let reject!: (error: Error) => void
  const promise = new Promise<HistoryList>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
const flush = async () => { await Promise.resolve(); await Promise.resolve() }
afterEach(() => { scopes.splice(0).forEach(scope => scope.stop()); vi.useRealTimers(); vi.unstubAllGlobals() })

describe('server history page state', () => {
  it.each([0, 1, 20, 21, 105])('loads bounded pages and clamps navigation for %i records', async (count) => {
    const all = rows(count)
    const loader = vi.fn(async (q: HistoryQuery) => ({ items: all.slice(q.offset, (q.offset ?? 0) + 20), total: all.length }))
    const state = useList(loader)
    await state.refresh()
    expect(state.records.value).toHaveLength(Math.min(20, count))
    expect(state.total.value).toBe(count)
    expect(state.pageCount.value).toBe(Math.max(1, Math.ceil(count / 20)))
    await state.goToPage(999)
    expect(state.page.value).toBe(state.pageCount.value)
    await state.goToPage(-1)
    expect(state.page.value).toBe(1)
  })
  it('debounces Chinese search, resets the page and sends all three filters', async () => {
    vi.useFakeTimers()
    const loader = vi.fn(async () => ({ items: rows(1), total: 21 }))
    const state = useList(loader)
    await state.refresh(2)
    state.search.value = ' 中文阅读 '
    expect(state.page.value).toBe(1)
    expect(state.loading.value).toBe(true)
    await vi.advanceTimersByTimeAsync(249)
    expect(loader).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(loader).toHaveBeenLastCalledWith({ q: '中文阅读', ai_filter: 'all', limit: 20, offset: 0 })
    for (const filter of ['with-ai', 'without-ai', 'all'] as const) {
      state.aiFilter.value = filter; await flush()
      expect(loader).toHaveBeenLastCalledWith({ q: '中文阅读', ai_filter: filter, limit: 20, offset: 0 })
    }
  })
  it('ignores stale success during debounce and stale failure after a newer response', async () => {
    vi.useFakeTimers()
    const first = deferred(), second = deferred(), third = deferred()
    const loader = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise).mockReturnValueOnce(third.promise)
    const state = useList(loader)
    const pending = state.refresh()
    state.search.value = '甲'
    first.resolve({ items: rows(21), total: 21 }); await pending
    expect(state.records.value).toEqual([])
    expect(state.loading.value).toBe(true)
    await vi.advanceTimersByTimeAsync(250)
    state.search.value = '乙'
    await vi.advanceTimersByTimeAsync(250)
    third.resolve({ items: rows(1), total: 1 }); await flush()
    second.reject(new Error('过时错误')); await flush()
    expect(state.records.value).toHaveLength(1)
    expect(state.total.value).toBe(1)
    expect(state.error.value).toBe('')
    expect(state.loading.value).toBe(false)
  })
  it('never lets an old success replace a completed newer search', async () => {
    vi.useFakeTimers()
    const old = deferred()
    const loader = vi.fn().mockReturnValueOnce(old.promise).mockResolvedValue({ items: rows(1), total: 1 })
    const state = useList(loader)
    const pending = state.refresh()
    state.search.value = '新搜索'
    await vi.advanceTimersByTimeAsync(250)
    old.resolve({ items: rows(20), total: 20 }); await pending
    expect(state.total.value).toBe(1)
    expect(state.records.value).toHaveLength(1)
  })
  it('refills deletion pages and goes back when the last page becomes empty', async () => {
    const all = rows(21)
    const loader = vi.fn(async (q: HistoryQuery) => ({ items: all.slice(q.offset, (q.offset ?? 0) + 20), total: all.length }))
    const state = useList(loader)
    await state.refresh(2)
    all.pop(); await state.refresh()
    expect(state.page.value).toBe(1)
    expect(state.total.value).toBe(20)
    expect(state.records.value).toHaveLength(20)
    all.shift(); await state.refresh()
    expect(state.records.value[0].id).toBe(20)
    expect(state.total.value).toBe(19)
    all.splice(0); await state.refresh()
    expect(state.page.value).toBe(1)
    expect(state.records.value).toEqual([])
    expect(state.total.value).toBe(0)
  })
  it('surfaces current errors, retries and cancels scheduled work on disposal', async () => {
    vi.useFakeTimers()
    const loader = vi.fn().mockRejectedValueOnce(new Error('本地服务不可用')).mockResolvedValue({ items: [], total: 0 })
    const state = useList(loader)
    await state.refresh()
    expect(state.error.value).toBe('本地服务不可用')
    await state.refresh()
    expect(state.error.value).toBe('')
    state.search.value = '尚未发送'; scopes[0].stop()
    await vi.advanceTimersByTimeAsync(250)
    expect(loader).toHaveBeenCalledTimes(2)
  })
  it('retains the page when opening, exporting and returning to a history record', async () => {
    const all = rows(21)
    const detail = { id: 1, question: '合成占问 1', method: 'manual', created_at: '2026-10-16T00:00:00Z',
      lines: [], changed_lines: [], moving_positions: [1], base_hexagram: { title: '乾', judgment: '示例卦辞', line_texts: ['示例初爻'] },
      changed_hexagram: { title: '姤', judgment: '示例之卦' }, traditional_reading: null } as unknown as Divination
    vi.stubGlobal('fetch', vi.fn(async (path: string) => {
      const url = new URL(path, 'http://localhost'), offset = Number(url.searchParams.get('offset'))
      const data = url.pathname === '/api/history/1' ? detail : { items: all.slice(offset, offset + 20), total: all.length }
      return new Response(JSON.stringify(data), { status: 200 })
    }))
    const state = useList(api.history)
    await state.refresh(2)
    const opened = await api.historyItem(state.records.value[0].id)
    expect(divinationMarkdown(opened)).toContain('示例初爻')
    expect(divinationMarkdown(opened)).toContain('合成占问 1')
    await state.refresh()
    expect(state.page.value).toBe(2)
    expect(state.records.value.map(row => row.id)).toEqual([1])
  })
})
