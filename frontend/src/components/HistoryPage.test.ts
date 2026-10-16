import { createSSRApp, defineComponent, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import HistoryPage from './HistoryPage.vue'

async function renderEmptyHistory(overrides = {}) {
  const app = createSSRApp(HistoryPage, { records: [], loading: false, total: 0, page: 1, pageSize: 20, error: '', search: '', aiFilter: 'all', ...overrides })
  app.component('el-icon', defineComponent({ setup: (_, { slots }) => () => h('span', { 'aria-hidden': 'true' }, slots.default?.()) }))
  app.component('el-input', defineComponent({ setup: (_, { attrs }) => () => h('input', attrs) }))
  app.component('el-button', defineComponent({ setup: (_, { attrs, slots }) => () => h('button', attrs, slots.default?.()) }))
  app.directive('loading', () => {})
  return renderToString(app)
}

describe('HistoryPage empty state', () => {
  it('explains the empty history and offers a first-cast action', async () => {
    const html = await renderEmptyHistory()
    expect(html).toContain('还没有起卦记录')
    expect(html).toContain('记录会保存在本机')
    expect(html).toContain('开始第一次起卦')
    expect(html).toContain('按占问内容搜索历史')
    expect(html).toContain('按 AI 会话筛选')
    expect(html).toContain('第 1 / 1 页')
    expect(html).toContain('共 0 条')
  })
  it('distinguishes a filtered empty page from a brand new database', async () => {
    const html = await renderEmptyHistory({ search: '不存在' })
    expect(html).toContain('没有符合条件的记录')
    expect(html).toContain('清除筛选')
    expect(html).not.toContain('开始第一次起卦')
  })

  it('shows server totals, page boundaries and retryable errors', async () => {
    const html = await renderEmptyHistory({ total: 21, page: 2 })
    expect(html).toContain('共 21 条')
    expect(html).toContain('第 2 / 2 页')
    expect(html).toContain('下一页')
    expect(await renderEmptyHistory({ error: '请求失败' })).toContain('重试')
  })
})
