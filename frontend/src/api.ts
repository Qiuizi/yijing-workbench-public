import type { AIModel, AISettings, AISession, AISessionMessage, AIStreamResult, AppPreferences, Divination, HistoryList, NajiaChart, NajiaInput, NajiaOptions } from './types'
import { invoke, isTauri } from '@tauri-apps/api/core'

export class AIStreamError extends Error {
  constructor(message: string, readonly code: string, readonly stage: string) {
    super(message)
    this.name = 'AIStreamError'
  }
}

export interface AIDiagnosticEvent {
  event: 'sse_connected' | 'sse_done_received'
  sessionId: number
  requestId: string
  messageId?: number
  messageCount?: number
  status: string
  contentType?: string
  fields?: Record<string, boolean | number>
}

function aiMessageFieldSummary(message: AISessionMessage): Pick<AIDiagnosticEvent, 'messageId' | 'contentType' | 'fields'> {
  const content = message.content
  if (content && typeof content === 'object') {
    const fields: Record<string, boolean | number> = {}
    for (const [key, value] of Object.entries(content)) {
      fields[`${key}.present`] = value !== null && value !== undefined
      if (typeof value === 'string' || Array.isArray(value)) fields[`${key}.length`] = value.length
    }
    return { messageId: message.id, contentType: 'object', fields }
  }
  return {
    messageId: message.id,
    contentType: typeof content,
    fields: { 'content.present': content !== null && content !== undefined, 'content.length': typeof content === 'string' ? content.length : 0 },
  }
}

interface DesktopConnection { baseUrl: string; token: string }
interface DesktopMigrationStatus { can_import: boolean; history_count: number; ai_session_count: number; has_settings: boolean }
interface DesktopImportResult { imported: boolean; counts: Record<string, number>; backup_path: string; source_preserved: boolean }

async function appFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!isTauri()) return fetch(path, init)
  const connection = await invoke<DesktopConnection>('backend_connection')
  const headers = new Headers(init?.headers)
  headers.set('Authorization', `Bearer ${connection.token}`)
  return fetch(`${connection.baseUrl}${path}`, { ...init, headers })
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await appFetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (error) {
    if (isTauri() && error instanceof Error && error.message) {
      throw new Error(`桌面本地服务启动失败：${error.message}`)
    }
    throw new Error(isTauri() ? '桌面本地服务连接失败，请查看 yijing-backend.log。' : '无法连接本地服务，请确认后端已启动。')
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: { message?: string } } | null
    throw new Error(body?.error?.message ?? `请求失败（${response.status}）`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  desktopMigrationStatus: () => request<DesktopMigrationStatus>('/api/desktop/migration/status'),
  importDesktopDatabase: (sourcePath: string) => request<DesktopImportResult>('/api/desktop/migration/import', {
    method: 'POST', body: JSON.stringify({ source_path: sourcePath }),
  }),
  preferences: () => request<AppPreferences>('/api/preferences'),
  updatePreferences: (defaultMethod: 'coins' | 'manual', timezone: string, aiDefaultMode: 'classical' | 'najia') => request<AppPreferences>('/api/preferences', {
    method: 'PUT', body: JSON.stringify({ default_method: defaultMethod, timezone, ai_default_mode: aiDefaultMode }),
  }),
  cast: (question: string) => request<Divination>('/api/divination', {
    method: 'POST', body: JSON.stringify({ question }),
  }),
  castManual: (question: string, lines: number[]) => request<Divination>('/api/divination/manual', {
    method: 'POST', body: JSON.stringify({ question, lines }),
  }),
  history: () => request<HistoryList>('/api/history'),
  historyItem: (id: number) => request<Divination>(`/api/history/${id}`),
  deleteHistory: (id: number) => request<void>(`/api/history/${id}`, { method: 'DELETE' }),
  najiaOptions: () => request<NajiaOptions>('/api/najia/options'),
  createNajiaChart: (id: number, input: NajiaInput) => request<NajiaChart>(`/api/history/${id}/najia`, {
    method: 'POST', body: JSON.stringify(input),
  }),
  aiSettings: () => request<AISettings>('/api/ai/settings'),
  updateAiSettings: (payload: { api_key?: string; model_id?: string; ai_enabled?: boolean }) => request<AISettings>('/api/ai/settings', {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  deleteAiKey: () => request<void>('/api/ai/settings/key', { method: 'DELETE' }),
  aiModels: () => request<{ models: AIModel[] }>('/api/ai/models'),
  testAiConnection: () => request<{ ok: boolean; provider: string; available_models: number }>('/api/ai/test-connection', { method: 'POST' }),
  createAiSession: (divinationId: number, mode: 'classical' | 'najia') => request<AISession>('/api/ai/sessions', {
    method: 'POST', body: JSON.stringify({ divination_id: divinationId, mode }),
  }),
  aiSession: (id: number) => request<AISession>(`/api/ai/sessions/${id}`),
  aiSessionsForHistory: (id: number) => request<{ items: Array<{ id: number; mode: 'classical' | 'najia'; model_id: string; created_at: string }> }>(`/api/history/${id}/ai-sessions`),
  streamAiMessage: async (
    sessionId: number,
    message: string,
    requestId: string,
    signal: AbortSignal,
    onDelta: (text: string) => void,
    regenerateFromMessageId?: number,
    onReasoning?: (text: string) => void,
    onDiagnostic?: (event: AIDiagnosticEvent) => void,
  ): Promise<AIStreamResult> => {
    let response: Response
    try {
      response = await appFetch(`/api/ai/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify({ message, request_id: requestId, regenerate_from_message_id: regenerateFromMessageId }),
        signal,
      })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      if (isTauri() && error instanceof Error && error.message) throw new Error(`桌面本地服务启动失败：${error.message}`)
      throw new Error(isTauri() ? '桌面版 AI 本地服务连接失败，请查看 yijing-backend.log。' : '无法连接本地 AI 服务。')
    }
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { error?: { message?: string } } | null
      throw new Error(body?.error?.message ?? `请求失败（${response.status}）`)
    }
    if (!response.body) throw new AIStreamError('浏览器不支持读取流式响应。', 'stream_unavailable', 'transport')
    onDiagnostic?.({ event: 'sse_connected', sessionId, requestId, status: 'connected' })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalMessage: AIStreamResult | null = null
    const processFrame = (frame: string) => {
      let eventName = 'message'
      const data: string[] = []
      for (const line of frame.split(/\r?\n/)) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
      }
      if (!data.length) return
      let payload: {
        text?: string
        message?: AISessionMessage | string
        user_message?: AISessionMessage | string
        code?: string
        stage?: string
      }
      try {
        payload = JSON.parse(data.join('\n')) as typeof payload
      } catch {
        throw new AIStreamError('AI 流数据格式错误，未确认保存最终解读。', 'invalid_sse', 'transport')
      }
      if (eventName === 'reasoning' && typeof payload.text === 'string') onReasoning?.(payload.text)
      if (eventName === 'delta' && typeof payload.text === 'string') onDelta(payload.text)
      if (eventName === 'done') {
        if (!payload.message || typeof payload.message === 'string' || !payload.user_message || typeof payload.user_message === 'string') {
          throw new AIStreamError('AI 完成事件缺少已保存的会话消息。', 'invalid_done_event', 'transport')
        }
        finalMessage = { message: payload.message, user_message: payload.user_message }
        onDiagnostic?.({
          event: 'sse_done_received', sessionId, requestId, status: 'received',
          ...aiMessageFieldSummary(payload.message),
        })
      }
      if (eventName === 'error') {
        throw new AIStreamError(
          typeof payload.message === 'string' ? payload.message : 'AI 解读未完成，结果未保存。',
          typeof payload.code === 'string' ? payload.code : 'request_failed',
          typeof payload.stage === 'string' ? payload.stage : 'unknown',
        )
      }
    }
    try {
      while (true) {
        let chunk: ReadableStreamReadResult<Uint8Array>
        try {
          chunk = await reader.read()
        } catch (error) {
          if (error instanceof DOMException && error.name === 'AbortError') throw error
          throw new AIStreamError('AI 流式连接中断，结果是否保存尚未确认；可使用同一请求重试。', 'stream_interrupted', 'transport')
        }
        const { value, done } = chunk
        buffer += decoder.decode(value, { stream: !done })
        const frames = buffer.split(/\r?\n\r?\n/)
        buffer = frames.pop() ?? ''
        for (const frame of frames) processFrame(frame)
        if (done) break
      }
      if (buffer.trim()) processFrame(buffer)
    } finally {
      reader.releaseLock()
    }
    if (!finalMessage) throw new AIStreamError('AI 流没有收到完成事件，结果是否保存尚未确认；可使用同一请求重试。', 'missing_done', 'transport')
    return finalMessage
  },
}
