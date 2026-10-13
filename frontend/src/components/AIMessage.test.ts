import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import AIMessage from './AIMessage.vue'
import type { AIAssistantMessageView } from '../aiMessageModel'

const baseResult = {
  overview: '卦象概述测试内容',
  cited_passages: [],
  cited_rules: [],
  traditional_basis: '旧版传统依据内容',
  modern_interpretation: '结合问题的现代说明',
  suggestions: ['核对现实条件'],
  ruleset: { id: 'test', version: '1', name: '测试规则' },
  mode: 'classical' as const,
  caution: '仅供参考',
}

async function render(message: AIAssistantMessageView, statusLabel?: string) {
  return renderToString(createSSRApp(AIMessage, { message, statusLabel }))
}

describe('AIMessage presentation', () => {
  it('renders a saved legacy response as structured readable content', async () => {
    const html = await render({
      id: 1, requestId: 'old-request', turnMessageId: 2, role: 'assistant', status: 'complete',
      result: baseResult, content: '',
    })
    expect(html).toContain('卦象概述测试内容')
    expect(html).toContain('旧版传统依据内容')
    expect(html).toContain('结合问题的现代说明')
    expect(html).toContain('核对现实条件')
  })

  it('separates ai-response@2 explanation from locally injected source text', async () => {
    const html = await render({
      id: 3, requestId: 'v2-request', turnMessageId: 4, role: 'assistant', status: 'complete', content: '',
      result: {
        ...baseResult,
        response_schema: 'ai-response@2',
        cited_passages: [{ id: 'p1', label: '本卦卦辞', text: '来自本地资料的测试原文', source_url: 'https://example.test/source', source_revision_id: 19 }],
        traditional_basis: [{ evidence_id: 'p1', explanation: '模型解释该证据的含义。' }],
      },
    })
    expect(html).toContain('本地典籍资料')
    expect(html).toContain('来自本地资料的测试原文')
    expect(html).toContain('href="https://example.test/source"')
    expect(html).toContain('#19')
    expect(html).toContain('本卦卦辞')
    expect(html).toContain('模型解释该证据的含义。')
    expect(html).toContain('结合问题的现代说明')
  })

  it('keeps model reasoning collapsed and labels it as internal process', async () => {
    const html = await render({
      id: 'streaming:req-1', requestId: 'req-1', turnMessageId: null, role: 'assistant',
      status: 'streaming', model: 'mock-model', result: null, content: '', reasoningPreview: 'synthetic reasoning preview',
    }, '模型正在思考')
    expect(html).toContain('模型正在思考')
    expect(html).toContain('查看推理过程')
    expect(html).toContain('不属于最终解读')
    expect(html).not.toMatch(/<details[^>]*\sopen(?:=|\s|>)/)
    expect(html).not.toContain('卦象概述</h3>')
  })

  it('never renders an incompatible saved message as a blank assistant card', async () => {
    const html = await render({
      id: 5, requestId: null, turnMessageId: null, role: 'assistant', status: 'incompatible',
      result: null, content: '已保存的解读格式暂不支持展示。',
    })
    expect(html).toContain('已保存的解读格式暂不支持展示。')
  })
})
