import { describe, expect, it } from 'vitest'
import {
  mergeCompletedAiResult,
  mergeRefreshedAiSession,
  regenerateActionForAssistant,
  reloadAIViewSession,
  toAIViewSession,
} from './aiMessageModel'
import type { AIViewSession } from './aiMessageModel'
import type { AISession, AIStreamResult } from './types'

const interpretation = {
  overview: 'A saved overview that must remain visible.',
  cited_passages: [],
  cited_rules: [],
  traditional_basis: 'Verified basis',
  modern_interpretation: 'A concise modern reading.',
  suggestions: ['Consider the available evidence.'],
  ruleset: { id: 'qiming-tongshi', version: '1.0.0', name: '启蒙通释' },
  mode: 'classical' as const,
  caution: '仅供参考',
  provider: { model_id: 'deepseek-v4-pro', usage: null, cost_estimate: null },
}

const v2Interpretation = {
  response_schema: 'ai-response@2' as const,
  overview: 'V2 summary',
  cited_passages: [{
    id: 'p1', label: '卦辞', text: '本地数据库原文',
    source_url: 'https://example.test/source', source_revision_id: 42,
  }],
  cited_rules: [],
  traditional_basis: [{ evidence_id: 'p1', explanation: 'AI 对该段证据的解释。' }],
  modern_interpretation: '结合问题的解释',
  suggestions: ['核对现实条件'],
  ruleset: { id: 'qiming-tongshi', version: '1.0.0', name: '启蒙通释' },
  mode: 'classical' as const,
  caution: '仅供参考',
  provider: { model_id: 'deepseek-v4-pro', usage: null, cost_estimate: null },
}

function session(messages: AISession['messages'] = []): AISession {
  return {
    id: 1, divination_id: 9, mode: 'classical', model_id: 'deepseek-v4-pro',
    created_at: '2026-01-01T00:00:00Z', messages,
  }
}

function lastAssistant(messages: AIViewSession['messages']) {
  const last = messages.at(-1)
  return last?.role === 'assistant' ? last : null
}

describe('AI message view model', () => {
  it('restores a persisted assistant object as a visible result', () => {
    const restored = toAIViewSession(session([
      { id: 1, role: 'user', content: 'synthetic test question', created_at: '2026-01-01T00:00:00Z' },
      { id: 2, role: 'assistant', content: interpretation, created_at: '2026-01-01T00:00:01Z' },
    ]))

    expect(restored.messages[1]).toMatchObject({
      id: 2, role: 'assistant', status: 'complete', model: 'deepseek-v4-pro', result: interpretation,
    })
    expect(restored.messages[1]?.role === 'assistant' && restored.messages[1].result?.overview.length).toBeGreaterThan(0)
  })

  it('maps a streaming done payload through the same model as session recovery', () => {
    const raw: AIStreamResult = {
      user_message: { id: 3, role: 'user', content: 'synthetic follow-up', created_at: '2026-01-01T00:00:02Z' },
      message: { id: 4, role: 'assistant', content: interpretation, created_at: '2026-01-01T00:00:02Z' },
    }
    const requestId = 'attempt-1'
    const restored = toAIViewSession(session([
      raw.user_message,
      { ...raw.message, request_id: requestId, user_message_id: raw.user_message.id },
    ]))
    const live = mergeCompletedAiResult(toAIViewSession(session()), raw, requestId)

    expect(live.messages).toEqual(restored.messages)
  })

  it('restores and immediately displays ai-response@2 in the same model as an SSE done result', () => {
    const raw: AIStreamResult = {
      user_message: { id: 13, role: 'user', content: 'synthetic question', created_at: '2026-01-01T00:00:02Z' },
      message: { id: 14, role: 'assistant', content: v2Interpretation, created_at: '2026-01-01T00:00:03Z' },
    }
    const persisted = toAIViewSession(session([
      raw.user_message,
      { ...raw.message, request_id: 'attempt-v2', user_message_id: raw.user_message.id },
    ]))
    const live = mergeCompletedAiResult(toAIViewSession(session()), raw, 'attempt-v2')
    const assistant = live.messages[1]

    expect(live.messages).toEqual(persisted.messages)
    expect(assistant?.role).toBe('assistant')
    if (assistant?.role === 'assistant') {
      expect(assistant.status).toBe('complete')
      expect(assistant.result?.response_schema).toBe('ai-response@2')
      expect(assistant.result?.cited_passages[0]?.text.length).toBeGreaterThan(0)
      expect(assistant.result?.traditional_basis).toEqual(v2Interpretation.traditional_basis)
    }
  })

  it('keeps a completed result when the follow-up session refresh is stale, fails, or returns the saved answer', async () => {
    const raw: AIStreamResult = {
      user_message: { id: 3, role: 'user', content: 'synthetic follow-up', created_at: '2026-01-01T00:00:02Z' },
      message: { id: 4, role: 'assistant', content: interpretation, created_at: '2026-01-01T00:00:02Z' },
    }
    const completed = mergeCompletedAiResult(toAIViewSession(session()), raw, 'attempt-1')
    const stale = toAIViewSession(session([raw.user_message, {
      ...raw.message, request_id: 'attempt-1', user_message_id: raw.user_message.id, content: {} as never,
    }]))

    expect(mergeRefreshedAiSession(stale, completed).messages.at(-1)).toMatchObject({
      id: 4, role: 'assistant', status: 'complete', result: interpretation,
    })
    expect(lastAssistant(completed.messages)?.result?.overview).toBe(interpretation.overview)

    const failed = await reloadAIViewSession(completed, async () => { throw new Error('mock reload failure') })
    expect(failed.ok).toBe(false)
    expect(lastAssistant(failed.session.messages)?.result?.overview).toBe(interpretation.overview)

    const successful = await reloadAIViewSession(completed, async () => session([
      raw.user_message,
      { ...raw.message, request_id: 'attempt-1', user_message_id: raw.user_message.id },
    ]))
    expect(successful.ok).toBe(true)
    expect(lastAssistant(successful.session.messages)?.result).toEqual(interpretation)
  })

  it('preserves old plain-text assistant messages and gives incompatible saved objects a visible status', () => {
    const restored = toAIViewSession(session([
      { id: 5, role: 'assistant', content: 'legacy saved answer', created_at: '2025-01-01T00:00:00Z' },
      { id: 6, role: 'assistant', content: {} as never, created_at: '2025-01-01T00:00:01Z' },
    ]))

    expect(restored.messages[0]).toMatchObject({ status: 'complete', content: 'legacy saved answer', result: null })
    expect(restored.messages[1]).toMatchObject({ status: 'incompatible', content: expect.stringContaining('缺少可展示字段') })
  })

  it('regenerates the last assistant attempt against its existing user turn', () => {
    const messages = toAIViewSession(session([
      { id: 10, role: 'user', content: 'synthetic original question', created_at: '2026-01-01T00:00:00Z' },
      { id: 11, role: 'assistant', content: interpretation, created_at: '2026-01-01T00:00:01Z' },
    ])).messages

    expect(regenerateActionForAssistant(messages, 1, 'attempt-2')).toEqual({
      kind: 'regenerate', message: 'synthetic original question', requestId: 'attempt-2', regenerateFromMessageId: 10,
    })
  })

  it('keeps two assistant attempts associated with one user without inserting another user', () => {
    const originalUser = { id: 10, role: 'user' as const, content: 'synthetic original question', created_at: '2026-01-01T00:00:00Z' }
    const first: AIStreamResult = {
      user_message: originalUser,
      message: { id: 11, role: 'assistant', content: interpretation, created_at: '2026-01-01T00:00:01Z' },
    }
    const retry: AIStreamResult = {
      user_message: originalUser,
      message: { id: 12, role: 'assistant', content: { ...interpretation, overview: 'second attempt' }, created_at: '2026-01-01T00:00:02Z' },
    }
    const withFirst = mergeCompletedAiResult(toAIViewSession(session()), first, 'attempt-1')
    const withRetry = mergeCompletedAiResult(withFirst, retry)

    expect(withRetry.messages.filter((item) => item.role === 'user')).toHaveLength(1)
    expect(withRetry.messages.filter((item) => item.role === 'assistant').map((item) => item.id)).toEqual([11, 12])
    expect(withRetry.messages.filter((item) => item.role === 'assistant').map((item) => item.turnMessageId)).toEqual([10, 10])
  })
})
