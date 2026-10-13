import type { AIFailedRequest, AIInterpretation, AISession, AISessionMessage, AIStreamResult } from './types'

export type AIMessageStatus = 'complete' | 'streaming' | 'incompatible'

export interface AIUserMessageView {
  id: number | string
  requestId: string | null
  turnMessageId: number
  role: 'user'
  status: 'complete'
  content: string
  created_at?: string
}

export interface AIAssistantMessageView {
  id: number | string
  requestId: string | null
  turnMessageId: number | null
  role: 'assistant'
  status: AIMessageStatus
  model?: string
  result: AIInterpretation | null
  content: string
  reasoningPreview?: string
  created_at?: string
}

export type AIMessageView = AIUserMessageView | AIAssistantMessageView

export interface AIViewSession extends Omit<AISession, 'messages'> {
  messages: AIMessageView[]
  failed_requests?: AIFailedRequest[]
}

export interface AIRetryAction {
  kind: 'send' | 'regenerate'
  message: string
  requestId: string
  regenerateFromMessageId?: number
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function parseAssistantResult(content: unknown): AIInterpretation | null {
  if (isRecord(content)) return content as unknown as AIInterpretation
  if (typeof content !== 'string') return null
  try {
    const parsed: unknown = JSON.parse(content)
    return isRecord(parsed) ? parsed as unknown as AIInterpretation : null
  } catch {
    return null
  }
}

function hasDisplayField(result: AIInterpretation | null): boolean {
  return Boolean(result && [
    result.overview,
    result.traditional_basis,
    result.modern_interpretation,
    result.caution,
  ].some((value) => typeof value === 'string' && value.length > 0))
}

/** Convert either a restored database message or an SSE message to the same UI model. */
export function toAIMessageView(
  message: AISessionMessage,
  options: { requestId?: string | null; model?: string; turnMessageId?: number | null } = {},
): AIMessageView {
  if (message.role === 'user') {
    return {
      id: message.id,
      requestId: options.requestId ?? message.request_id ?? null,
      turnMessageId: message.id,
      role: 'user',
      status: 'complete',
      content: typeof message.content === 'string' ? message.content : '',
      created_at: message.created_at,
    }
  }

  const result = parseAssistantResult(message.content)
  const legacyText = typeof message.content === 'string' && result === null ? message.content : ''
  const status: AIMessageStatus = result && hasDisplayField(result)
    ? 'complete'
    : legacyText
      ? 'complete'
      : 'incompatible'
  return {
    id: message.id,
    requestId: options.requestId ?? message.request_id ?? null,
    turnMessageId: options.turnMessageId ?? message.user_message_id ?? null,
    role: 'assistant',
    status,
    model: options.model,
    result: result && hasDisplayField(result) ? result : null,
    content: legacyText || (status === 'incompatible' ? '已保存的解读缺少可展示字段，原记录仍已保留。' : ''),
    created_at: message.created_at,
  }
}

export function toAIViewSession(session: AISession): AIViewSession {
  return {
    ...session,
    messages: session.messages.map((message) => toAIMessageView(message, { model: session.model_id })),
  }
}

export function streamingAssistantMessage(
  requestId: string,
  model: string,
  reasoningPreview = '',
): AIAssistantMessageView {
  return {
    id: `streaming:${requestId}`,
    requestId,
    turnMessageId: null,
    role: 'assistant',
    status: 'streaming',
    model,
    result: null,
    content: '',
    reasoningPreview,
  }
}

export function regenerateActionForAssistant(
  messages: AIMessageView[], assistantIndex: number, requestId: string,
): AIRetryAction | null {
  if (messages[assistantIndex]?.role !== 'assistant') return null
  const user = messages.slice(0, assistantIndex).reverse().find((message) => message.role === 'user')
  if (!user || user.role !== 'user' || typeof user.content !== 'string') return null
  return {
    kind: 'regenerate',
    message: user.content,
    requestId,
    regenerateFromMessageId: typeof user.id === 'number' ? user.id : undefined,
  }
}

/** Merge the server's committed exchange before attempting a session refresh. */
export function mergeCompletedAiResult(session: AIViewSession, result: AIStreamResult, requestId?: string): AIViewSession {
  const incoming = [
    toAIMessageView(result.user_message),
    toAIMessageView(result.message, { model: session.model_id, requestId, turnMessageId: result.user_message.id }),
  ]
  const messages = [...session.messages]
  for (const message of incoming) {
    const existingIndex = messages.findIndex((item) => item.id === message.id)
    if (existingIndex >= 0) messages[existingIndex] = message
    else messages.push(message)
  }
  return { ...session, messages }
}

/** Keep a just-confirmed answer when an eventually consistent refresh returns an older row. */
export function mergeRefreshedAiSession(refreshed: AIViewSession, current: AIViewSession): AIViewSession {
  const messages = [...refreshed.messages]
  for (const local of current.messages) {
    const index = messages.findIndex((item) => item.id === local.id)
    if (index < 0) {
      messages.push(local)
      continue
    }
    const server = messages[index]
    if (server.role === 'assistant' && local.role === 'assistant'
      && server.status !== 'complete' && local.status === 'complete') {
      messages[index] = local
    }
  }
  messages.sort((left, right) => {
    if (typeof left.id === 'number' && typeof right.id === 'number') return left.id - right.id
    if (typeof left.id === 'number') return -1
    if (typeof right.id === 'number') return 1
    return String(left.id).localeCompare(String(right.id))
  })
  return { ...refreshed, messages }
}

export type AIRefreshResult =
  | { ok: true; session: AIViewSession; wire: AISession }
  | { ok: false; session: AIViewSession; error: unknown }

export async function reloadAIViewSession(
  current: AIViewSession,
  load: () => Promise<AISession>,
): Promise<AIRefreshResult> {
  try {
    const wire = await load()
    return { ok: true, session: mergeRefreshedAiSession(toAIViewSession(wire), current), wire }
  } catch (error) {
    return { ok: false, session: current, error }
  }
}
