import { afterEach, describe, expect, it, vi } from 'vitest'
import { invoke, isTauri } from '@tauri-apps/api/core'
import { api } from './api'
import { toAIViewSession } from './aiMessageModel'
import type { AISessionMessage } from './types'

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
  isTauri: vi.fn(() => false),
}))

const interpretation = {
  overview: '概述',
  cited_passages: [{ id: 'p1', label: '初九', text: '原文', source_url: 'https://example.test', source_revision_id: 1 }],
  traditional_basis: '依据',
  modern_interpretation: '解释',
  suggestions: ['建议'],
  ruleset: { id: 'qiming-tongshi', version: '1.0.0', name: '启蒙通释' },
  mode: 'classical' as const,
  caution: '注意',
  provider: { model_id: 'deepseek-v4-pro', usage: null, cost_estimate: null },
}

function streamingResponse(events: string[]) {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of events) controller.enqueue(encoder.encode(event))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

function byteSplitStreamingResponse(event: string) {
  const bytes = new TextEncoder().encode(event)
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const byte of bytes) controller.enqueue(Uint8Array.of(byte))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.mocked(isTauri).mockReturnValue(false)
  vi.mocked(invoke).mockReset()
})

describe('Tauri desktop API transport', () => {
  it('encodes server history search and pagination independently', async () => {
    vi.mocked(isTauri).mockReturnValue(false)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"items":[],"total":0}')))
    await api.history({ q: '中文 &%_?', ai_filter: 'without-ai', limit: 20, offset: 40 })
    const url = new URL(String(vi.mocked(fetch).mock.calls[0][0]), 'http://localhost')
    expect(url.pathname).toBe('/api/history')
    expect(Object.fromEntries(url.searchParams)).toEqual({ q: '中文 &%_?', ai_filter: 'without-ai', limit: '20', offset: '40' })
  })

  it('gets the rotating local connection over IPC and sends its bearer token', async () => {
    vi.mocked(isTauri).mockReturnValue(true)
    vi.mocked(invoke).mockResolvedValue({ baseUrl: 'http://127.0.0.1:8123', token: 'test-only-token' } as never)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    ))

    await api.history()

    expect(invoke).toHaveBeenCalledWith('backend_connection')
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toBe('http://127.0.0.1:8123/api/history')
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer test-only-token')
  })
})

describe('AI event stream API', () => {
  it('reads delta events split across transport chunks and resolves the structured result', async () => {
    const finalMessage: AISessionMessage = { id: 7, role: 'assistant', content: interpretation, created_at: '2026-01-01T00:00:00Z' }
    const userMessage: AISessionMessage = { id: 6, role: 'user', content: '解释一下', created_at: '2026-01-01T00:00:00Z' }
    const wire = `event: reasoning\ndata: ${JSON.stringify({ text: '临时过程' })}\n\nevent: delta\ndata: {"text":"{\\"overview\\":"}\n\nevent: done\ndata: ${JSON.stringify({ message: finalMessage, user_message: userMessage })}\n\n`
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(byteSplitStreamingResponse(wire)))
    const deltas: string[] = []
    const reasoning: string[] = []
    const diagnostics: Array<{ event: string; contentType?: string; fields?: Record<string, boolean | number> }> = []

    const result = await api.streamAiMessage(
      12, '解释一下', 'request-1', new AbortController().signal,
      (text) => deltas.push(text), undefined, (text) => reasoning.push(text),
      (event) => diagnostics.push(event),
    )

    expect(deltas).toEqual(['{"overview":'])
    expect(reasoning).toEqual(['临时过程'])
    expect(result).toEqual({ message: finalMessage, user_message: userMessage })
    expect(diagnostics.map((item) => item.event)).toEqual(['sse_connected', 'sse_done_received'])
    expect(diagnostics[1]).toMatchObject({
      messageId: 7,
      contentType: 'object',
      fields: { 'overview.present': true, 'overview.length': interpretation.overview.length },
    })
    expect((result.message.content as typeof interpretation).provider?.model_id).toBe('deepseek-v4-pro')
    expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/ai/sessions/12/messages', expect.objectContaining({ method: 'POST' }))
    expect(JSON.parse(String(vi.mocked(fetch).mock.calls[0][1]?.body))).toEqual({ message: '解释一下', request_id: 'request-1' })
  })

  it('preserves stable error code and stage from an SSE error event', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse([
      'event: error\ndata: {"code":"invalid_json","stage":"validation","message":"AI 没有返回完整 JSON"}\n\n',
    ])))
    await expect(api.streamAiMessage(1, '继续', 'request-2', new AbortController().signal, () => undefined))
      .rejects.toMatchObject({ code: 'invalid_json', stage: 'validation', message: 'AI 没有返回完整 JSON' })
  })

  it('distinguishes malformed SSE JSON, missing done, and interrupted connections', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse(['event: error\ndata: {broken}\n\n'])))
    await expect(api.streamAiMessage(1, '继续', 'request-3', new AbortController().signal, () => undefined))
      .rejects.toMatchObject({ code: 'invalid_sse', stage: 'transport' })

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse(['event: delta\ndata: {"text":"部分"}\n\n'])))
    await expect(api.streamAiMessage(1, '继续', 'request-4', new AbortController().signal, () => undefined))
      .rejects.toMatchObject({ code: 'missing_done', stage: 'transport' })

    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('event: delta\ndata: {"text":"部分"}\n\n'))
        controller.error(new Error('mock-only transport failure'))
      },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })))
    await expect(api.streamAiMessage(1, '继续', 'request-5', new AbortController().signal, () => undefined))
      .rejects.toMatchObject({ code: 'stream_interrupted', stage: 'transport' })
  })

  it('propagates cancellation so the page can stop generation', async () => {
    const abort = new DOMException('Aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort))
    await expect(api.streamAiMessage(1, '停止', 'request-6', new AbortController().signal, () => undefined))
      .rejects.toBe(abort)
  })

  it('restores a persisted failed request when reopening an AI session', async () => {
    const failedRequest = {
      request_id: 'failed-request-id',
      message_text: '继续分析',
      regenerate_from_message_id: null,
      code: 'invalid_json',
      stage: 'validation',
      message: 'AI 没有返回完整、可解析的 JSON，结果未保存。',
      created_at: '2026-01-01T00:00:00Z',
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      id: 12, divination_id: 4, mode: 'classical', model_id: 'deepseek-v4-pro',
      created_at: '2026-01-01T00:00:00Z', messages: [], failed_requests: [failedRequest],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    const restored = await api.aiSession(12)

    expect(restored.failed_requests).toEqual([failedRequest])
    expect(restored.messages).toEqual([])
  })

  it('maps saved session API content and assistant attempt links into the display model', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      id: 12, divination_id: 4, mode: 'classical', model_id: 'deepseek-v4-pro',
      created_at: '2026-01-01T00:00:00Z', failed_requests: [], messages: [
        { id: 20, role: 'user', content: 'synthetic question', created_at: '2026-01-01T00:00:00Z', request_id: null, user_message_id: null },
        { id: 21, role: 'assistant', content: interpretation, created_at: '2026-01-01T00:00:01Z', request_id: 'attempt-1', user_message_id: 20 },
      ],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    const view = toAIViewSession(await api.aiSession(12))
    const assistant = view.messages[1]

    expect(assistant).toMatchObject({
      id: 21, role: 'assistant', requestId: 'attempt-1', turnMessageId: 20,
      status: 'complete', result: interpretation,
    })
  })
})

describe('calendar API contract', () => {
  it('persists timezone, casting method, and the default AI interpretation mode', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ default_method: 'manual', timezone: 'UTC', ai_default_mode: 'najia', ruleset_id: 'qiming-tongshi', ruleset_version: '1.0.0' }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }),
    ))
    await api.updatePreferences('manual', 'UTC', 'najia')
    expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/preferences', expect.objectContaining({
      method: 'PUT', body: JSON.stringify({ default_method: 'manual', timezone: 'UTC', ai_default_mode: 'najia' }),
    }))
  })

  it('sends automatic local wall time and the selected IANA zone without rewriting either', async () => {
    const chart = { timestamp_source: 'automatic', calendar_context: null }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify(chart), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    ))

    await api.createNajiaChart(42, {
      source: 'automatic',
      local_datetime: '2025-02-03T22:09',
      timezone: 'Asia/Shanghai',
    })

    expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/history/42/najia', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        source: 'automatic',
        local_datetime: '2025-02-03T22:09',
        timezone: 'Asia/Shanghai',
      }),
    }))
  })
})
