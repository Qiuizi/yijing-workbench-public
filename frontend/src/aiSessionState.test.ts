import { describe, expect, it } from 'vitest'
import { mergeCompletedAiResult, retryActionFromFailure } from './aiSessionState'
import { toAIViewSession } from './aiMessageModel'
import type { AIFailedRequest, AISession, AIStreamResult } from './types'
import type { AIMessageView } from './aiMessageModel'

const session: AISession = {
  id: 4,
  divination_id: 9,
  mode: 'classical',
  model_id: 'deepseek-test-model',
  created_at: '2026-01-01T00:00:00Z',
  messages: [
    { id: 1, role: 'user', content: '此前问题', created_at: '2026-01-01T00:00:00Z' },
    { id: 2, role: 'assistant', content: '此前成功回答', created_at: '2026-01-01T00:00:01Z' },
  ],
}

const interpretation = {
  overview: '保存后应立即显示的卦象概述',
  cited_passages: [],
  cited_rules: [],
  traditional_basis: '取辞依据',
  modern_interpretation: '结合问题的说明',
  suggestions: ['核对现实条件'],
  ruleset: { id: 'qiming-tongshi', version: '1.0.0', name: '启蒙通释' },
  mode: 'classical' as const,
  caution: '仅供参考',
  provider: { model_id: 'deepseek-v4-pro', usage: null, cost_estimate: null },
}

const result: AIStreamResult = {
  user_message: { id: 3, role: 'user', content: '本次追问', created_at: '2026-01-01T00:00:02Z' },
  message: { id: 4, role: 'assistant', content: interpretation, created_at: '2026-01-01T00:00:02Z' },
}

function lastAssistant(messages: AIMessageView[]) {
  const last = messages.at(-1)
  return last?.role === 'assistant' ? last : null
}

describe('AI completed response state', () => {
  it('shows a server-committed answer immediately and preserves prior answers if refresh fails', () => {
    const displayed = mergeCompletedAiResult(toAIViewSession(session), result)
    expect(displayed.messages.slice(0, 3).map((item) => item.role === 'assistant' ? item.result?.overview ?? item.content : item.content)).toEqual([
      '此前问题', '此前成功回答', '本次追问',
    ])
    expect(lastAssistant(displayed.messages)?.result).toEqual(interpretation)
    // A failed reload does not replace this state; the committed SSE done payload remains visible.
    expect(() => { throw new Error('mock refresh failure') }).toThrow('mock refresh failure')
    expect(lastAssistant(displayed.messages)?.result).toEqual(interpretation)
  })

  it('is idempotent when the same saved completion is replayed after a lost done event', () => {
    const once = mergeCompletedAiResult(toAIViewSession(session), result)
    const twice = mergeCompletedAiResult(once, result)
    expect(twice.messages).toEqual(once.messages)
  })

  it('restores a failed send with the same request id and original prompt', () => {
    const failed: AIFailedRequest = {
      request_id: 'request-to-retry', message_text: '继续分析', regenerate_from_message_id: null,
      code: 'invalid_json', stage: 'validation', message: 'AI 没有返回可解析 JSON。',
      created_at: '2026-01-01T00:00:00Z',
    }

    expect(retryActionFromFailure(failed)).toEqual({
      kind: 'send', message: '继续分析', requestId: 'request-to-retry', regenerateFromMessageId: undefined,
    })
  })

  it('restores a failed regeneration target without creating another user message', () => {
    const failed: AIFailedRequest = {
      request_id: 'request-to-regenerate', message_text: '原始问题', regenerate_from_message_id: 12,
      code: 'output_truncated', stage: 'generation', message: '回答未完成。',
      created_at: '2026-01-01T00:00:00Z',
    }

    expect(retryActionFromFailure(failed)).toEqual({
      kind: 'regenerate', message: '原始问题', requestId: 'request-to-regenerate', regenerateFromMessageId: 12,
    })
  })
})
