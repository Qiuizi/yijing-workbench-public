<script setup lang="ts">
import { computed, h, nextTick, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AIStreamError, api, type AIDiagnosticEvent } from '../api'
import { DEEPSEEK_PLATFORM_TERMS_URL, DEEPSEEK_PRIVACY_URL, markAIPrivacyAcknowledged } from '../aiPrivacyNotice'
import { mergeCompletedAiResult, retryActionFromFailure, type AIRetryAction } from '../aiSessionState'
import { regenerateActionForAssistant, reloadAIViewSession, streamingAssistantMessage, toAIViewSession, type AIAssistantMessageView, type AIMessageView, type AIViewSession } from '../aiMessageModel'
import AIMessage from './AIMessage.vue'
import AIRequestStatus from './AIRequestStatus.vue'
import { aiFailureStageLabel, aiFailureTitle, aiPhaseHelp, aiPhaseLabel, aiProgressSteps, type AIRequestPhase } from '../aiPresentation'
import type { AIFailedRequest, AISettings, AISessionMessage, Divination } from '../types'

const props = defineProps<{ divination: Divination | null }>()
const emit = defineEmits<{ startCasting: [] }>()
const settings = ref<AISettings | null>(null)
const session = ref<AIViewSession | null>(null)
const sessions = ref<Array<{ id: number; mode: 'classical' | 'najia'; model_id: string; rule_versions?: Record<string, unknown>; created_at: string }>>([])
const mode = ref<'classical' | 'najia'>('classical')
const defaultMode = ref<'classical' | 'najia'>('classical')
const compose = ref('请结合这次卦象和我的问题，给出结构化说明。')
const busy = ref(false)
const requestPhase = ref<AIRequestPhase>('waiting')
const streamingChars = ref(0)
const streamingReasoning = ref('')
const lastFailure = ref<{ code: string; stage: string; message: string } | null>(null)
const pendingRetry = ref<AIRetryAction | null>(null)
const messageList = ref<HTMLElement | null>(null)
type AIFrontendDiagnostic = AIDiagnosticEvent | {
  event: 'session_loaded' | 'assistant_loaded' | 'assistant_state_updated' | 'assistant_render_ready'
  sessionId: number
  requestId?: string
  messageId?: number | string
  status: string
  contentType?: string
  fields?: Record<string, boolean | number>
  messageCount?: number
}
const diagnosticEvents = ref<AIFrontendDiagnostic[]>([])
const showAIDiagnostics = import.meta.env.DEV
let controller: AbortController | null = null

const canUseNajia = computed(() => Boolean(props.divination?.najia_chart))
const ready = computed(() => Boolean(settings.value?.ai_enabled && props.divination?.id !== null && props.divination?.id !== undefined))
const currentFailure = computed(() => {
  if (lastFailure.value) return lastFailure.value
  const messages = session.value?.messages ?? []
  const unresolved = (session.value?.failed_requests ?? []).filter((failure) =>
    !messages.some((message) => message.role === 'assistant' && message.requestId === failure.request_id),
  )
  return unresolved.at(-1) ?? null
})
const hasCompletedAnswer = computed(() => Boolean(session.value?.messages.some((message) => message.role === 'assistant' && message.status === 'complete')))
const visiblePhase = computed<AIRequestPhase>(() => {
  if (busy.value) return requestPhase.value
  if (lastFailure.value?.stage === 'refresh' && hasCompletedAnswer.value) return 'complete'
  if (currentFailure.value) return currentFailure.value.stage === 'cancelled' ? 'cancelled' : 'failed'
  if (hasCompletedAnswer.value) return 'complete'
  return 'waiting'
})
const statusLabel = computed(() => aiPhaseLabel(visiblePhase.value))
const statusHelp = computed(() => aiPhaseHelp(visiblePhase.value, ready.value, streamingChars.value))
const progressSteps = computed(() => aiProgressSteps(visiblePhase.value, currentFailure.value?.stage))
const displayMessages = computed<AIMessageView[]>(() => {
  const saved = [...(session.value?.messages ?? [])]
  if (busy.value && session.value && pendingRetry.value) {
    saved.push(streamingAssistantMessage(
      pendingRetry.value.requestId,
      session.value.model_id,
      streamingReasoning.value,
    ))
  }
  return saved
})

function recordDiagnostic(event: AIFrontendDiagnostic) {
  if (!showAIDiagnostics) return
  diagnosticEvents.value = [...diagnosticEvents.value.slice(-39), event]
  console.info('[yijing-ai-ui]', event)
}

function messageDiagnostic(message: AISessionMessage | AIMessageView, sessionId: number): AIFrontendDiagnostic {
  const wireContent = message.content
  const result = 'result' in message ? message.result : message.role === 'assistant' && wireContent && typeof wireContent === 'object' ? wireContent : null
  const content = message.role === 'user' ? message.content : result
  const fields: Record<string, boolean | number> = {
    'content.present': content !== null && content !== undefined,
    'result.present': Boolean(result),
  }
  if (typeof content === 'string') fields['content.length'] = content.length
  if (result && typeof result === 'object') {
    const resultFields = result as unknown as Record<string, unknown>
    for (const key of ['overview', 'modern_interpretation', 'caution']) {
      const value = resultFields[key]
      fields[`${key}.present`] = typeof value === 'string'
      if (typeof value === 'string') fields[`${key}.length`] = value.length
    }
    const basis = resultFields.traditional_basis
    fields['traditional_basis.present'] = typeof basis === 'string' || Array.isArray(basis)
    if (typeof basis === 'string') fields['traditional_basis.length'] = basis.length
    if (Array.isArray(basis)) fields['traditional_basis.length'] = basis.length
    for (const key of ['cited_passages', 'cited_rules', 'suggestions']) {
      const value = resultFields[key]
      fields[`${key}.present`] = Array.isArray(value)
      if (Array.isArray(value)) fields[`${key}.length`] = value.length
    }
  }
  return {
    event: 'assistant_loaded', sessionId, messageId: message.id,
    requestId: 'requestId' in message ? message.requestId ?? undefined : message.request_id ?? undefined,
    status: 'status' in message ? message.status : 'restored',
    contentType: typeof wireContent === 'string' ? 'string' : wireContent === null ? 'null' : typeof wireContent,
    fields,
  }
}

function logRestoredSession(wire: Awaited<ReturnType<typeof api.aiSession>>, view: AIViewSession) {
  recordDiagnostic({ event: 'session_loaded', sessionId: view.id, status: 'loaded', messageCount: view.messages.length })
  wire.messages.forEach((message, index) => {
    if (message.role !== 'assistant') return
    const mapped = view.messages[index]
    if (mapped?.role === 'assistant') recordDiagnostic(messageDiagnostic(message, view.id))
  })
}

async function logRenderedAssistants() {
  await nextTick()
  if (!session.value) return
  const cards = Array.from(messageList.value?.querySelectorAll<HTMLElement>('.ai-message--assistant:not([data-status="streaming"])') ?? [])
  const assistants = displayMessages.value.filter((message): message is AIAssistantMessageView =>
    message.role === 'assistant' && message.status !== 'streaming',
  )
  assistants.forEach((message, index) => {
    const card = cards[index]
    const result = message.result
    recordDiagnostic({
      event: 'assistant_render_ready', sessionId: session.value!.id, messageId: message.id,
      requestId: message.requestId ?? undefined, status: message.status,
      contentType: result ? 'object' : 'string',
      fields: {
        'result.present': Boolean(result),
        'overview.length': result?.overview?.length ?? 0,
        'traditional_basis.length': result?.traditional_basis?.length ?? 0,
        'modern_interpretation.length': result?.modern_interpretation?.length ?? 0,
        'dom_text.length': card?.textContent?.length ?? 0,
      },
    })
  })
}

async function loadSavedSessions() {
  session.value = null
  sessions.value = []
  lastFailure.value = null
  pendingRetry.value = null
  requestPhase.value = 'waiting'
  if (!props.divination?.id) return
  try {
    const response = await api.aiSessionsForHistory(props.divination.id)
    sessions.value = response.items
    const latest = response.items.at(-1)
    if (latest) await openSession(latest.id)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取 AI 会话失败。')
  }
}

async function refreshSettings() {
  try {
    settings.value = await api.aiSettings()
    defaultMode.value = (await api.preferences()).ai_default_mode
    if (!session.value) mode.value = defaultMode.value
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取 AI 状态失败。')
  }
}

async function openSession(id: number) {
  try {
    const wire = await api.aiSession(id)
    session.value = toAIViewSession(wire)
    logRestoredSession(wire, session.value)
    recordDiagnostic({ event: 'assistant_state_updated', sessionId: session.value.id, status: 'session_restored', messageCount: session.value.messages.length })
    mode.value = session.value.mode
    lastFailure.value = null
    const latestFailure = session.value.failed_requests?.at(-1)
    if (latestFailure) {
      const action = retryActionFromFailure(latestFailure)
      pendingRetry.value = action
      if (action.kind === 'send') compose.value = action.message
    } else {
      pendingRetry.value = null
    }
    requestPhase.value = currentFailure.value ? (currentFailure.value.stage === 'cancelled' ? 'cancelled' : 'failed')
      : session.value.messages.some((message) => message.role === 'assistant' && message.status === 'complete') ? 'complete' : 'waiting'
    await scrollMessagesToLatest()
    await logRenderedAssistants()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '打开 AI 会话失败。')
  }
}

function startNewSession() {
  session.value = null
  mode.value = defaultMode.value
  lastFailure.value = null
  pendingRetry.value = null
  requestPhase.value = 'waiting'
  compose.value = '请结合这次卦象和我的问题，给出结构化说明。'
}

async function reloadSession() {
  if (!session.value) return
  const current = session.value
  const reload = await reloadAIViewSession(current, () => api.aiSession(current.id))
  session.value = reload.session
  if (!reload.ok) throw reload.error
  recordDiagnostic({ event: 'assistant_state_updated', sessionId: session.value.id, status: 'session_reloaded', messageCount: session.value.messages.length })
  const wire = reload.wire
  const refreshed = toAIViewSession(wire)
  logRestoredSession(wire, refreshed)
  await logRenderedAssistants()
}

async function scrollMessagesToLatest() {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

function confirmText(message: string, targetMessageId?: number) {
  const selectedMode = session.value?.mode ?? mode.value
  const modeLabel = selectedMode === 'classical' ? '《周易》经文辅助' : '六爻纳甲辅助'
  const contextLabel = selectedMode === 'classical'
    ? '发送本卦、动爻、变卦、所选取辞原文及规则版本。'
    : '发送本卦、动爻、变卦及本次纳甲排盘和启用的规则分析；不会发送经文取辞内容。'
  const targetIndex = targetMessageId
    ? session.value?.messages.findIndex((item) => item.id === targetMessageId) ?? -1
    : -1
  const priorCount = targetIndex >= 0 ? targetIndex : session.value?.messages.length ?? 0
  const actionLabel = targetMessageId ? '重新生成该条回答' : '发送本条消息'
  return [
    `即将${actionLabel}并调用第三方服务 DeepSeek。`,
    `模型：${session.value?.model_id ?? settings.value?.model_id ?? '当前设置模型'}`,
    `模式：${modeLabel}`,
    `本次消息：${message}`,
    `起卦问题：${props.divination?.question ?? ''}`,
    contextLabel,
    `当前会话将附带此前 ${priorCount} 条消息作为多轮上下文；不会自动读取或发送其他历史会话。`,
  ].join('\n\n')
}

async function confirmExternalSend(action: NonNullable<typeof pendingRetry.value>) {
  const paragraphs = confirmText(action.message, action.regenerateFromMessageId).split('\n\n')
  const content = h('div', { class: 'ai-consent-detail' }, [
    ...paragraphs.map((paragraph) => h('p', paragraph)),
    h('p', 'API Key 会通过 HTTPS Bearer 身份验证发送给 DeepSeek，用于验证 API 账户，不会作为提示词内容。请求数据由服务方按适用的开放平台条款处理；本应用不承诺服务方不会保存数据。'),
    h('p', [
      'DeepSeek 隐私政策：',
      h('a', { href: DEEPSEEK_PRIVACY_URL, target: '_blank', rel: 'noopener noreferrer' }, '查看政策'),
      '；开放平台条款：',
      h('a', { href: DEEPSEEK_PLATFORM_TERMS_URL, target: '_blank', rel: 'noopener noreferrer' }, '查看条款'),
    ]),
  ])
  await ElMessageBox.confirm(content, '发送资料前确认', {
    confirmButtonText: '同意并发送',
    cancelButtonText: '取消',
    type: 'warning',
    distinguishCancelAndClose: true,
    dangerouslyUseHTMLString: false,
  })
  markAIPrivacyAcknowledged()
}

async function runAction(action: NonNullable<typeof pendingRetry.value>) {
  if (busy.value) return
  if (!ready.value || !props.divination?.id) {
    ElMessage.warning('请先保存一次起卦记录，并在设置中启用 AI。')
    return
  }
  if ((session.value?.mode ?? mode.value) === 'najia' && !canUseNajia.value) {
    ElMessage.warning('请先在“六爻排盘”页面完成纳甲排盘。')
    return
  }
  try {
    await confirmExternalSend(action)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '确认发送失败。')
    return
  }

  pendingRetry.value = action
  lastFailure.value = null
  busy.value = true
  requestPhase.value = 'connecting'
  streamingChars.value = 0
  streamingReasoning.value = ''
  try {
    if (!session.value || session.value.mode !== mode.value) {
      session.value = toAIViewSession(await api.createAiSession(props.divination.id, mode.value))
      sessions.value.push({
        id: session.value.id,
        mode: session.value.mode,
        model_id: session.value.model_id,
        rule_versions: session.value.rule_versions,
        created_at: session.value.created_at,
      })
    }
    controller = new AbortController()
    const result = await api.streamAiMessage(
      session.value.id,
      action.message,
      action.requestId,
      controller.signal,
      (delta) => { streamingChars.value += delta.length; requestPhase.value = 'generating' },
      action.regenerateFromMessageId,
      (delta) => { streamingReasoning.value += delta; if (requestPhase.value !== 'generating') requestPhase.value = 'thinking' },
      (event) => {
        if (event.event === 'sse_connected') requestPhase.value = 'thinking'
        if (event.event === 'sse_done_received') requestPhase.value = 'complete'
        recordDiagnostic(event)
      },
    )
    const merged = mergeCompletedAiResult(session.value, result, action.requestId)
    session.value = {
      ...merged,
      failed_requests: merged.failed_requests?.filter((item) => item.request_id !== action.requestId),
    }
    recordDiagnostic({ event: 'assistant_state_updated', sessionId: session.value.id, requestId: action.requestId, messageId: result.message.id, status: 'completed_from_sse', messageCount: session.value.messages.length })
    await logRenderedAssistants()
    await scrollMessagesToLatest()
    if (action.kind === 'send' && compose.value.trim() === action.message) compose.value = ''
    pendingRetry.value = null
    try {
      await reloadSession()
    } catch {
      lastFailure.value = {
        code: 'session_refresh_failed',
        stage: 'refresh',
        message: '解读已经保存并显示，但会话刷新失败；重新打开此记录仍可读取已保存内容。',
      }
      ElMessage.warning(lastFailure.value.message)
      await scrollMessagesToLatest()
    }
  } catch (error) {
    pendingRetry.value = action
    if (action.kind === 'send' && !compose.value.trim()) compose.value = action.message
    if (error instanceof DOMException && error.name === 'AbortError') {
      requestPhase.value = 'cancelled'
      lastFailure.value = {
        code: 'generation_cancelled', stage: 'cancelled',
        message: '生成已停止，尚未收到保存确认。使用同一请求重试会先检查是否已保存，不会重复写入。',
      }
      ElMessage.info(lastFailure.value.message)
    } else {
      requestPhase.value = 'failed'
      const message = error instanceof Error ? error.message : 'AI 解读失败，结果未保存。'
      lastFailure.value = error instanceof AIStreamError
        ? { code: error.code, stage: error.stage, message }
        : { code: 'unexpected_error', stage: 'processing', message }
      ElMessage.error(message)
    }
    try {
      await reloadSession()
      if (session.value?.failed_requests?.some((item) => item.request_id === action.requestId)) {
        lastFailure.value = null
      }
    } catch { /* The in-memory error remains visible if the service is unavailable. */ }
    await scrollMessagesToLatest()
  } finally {
    busy.value = false
    controller = null
    streamingChars.value = 0
    streamingReasoning.value = ''
  }
}

async function sendMessage() {
  const message = compose.value.trim()
  if (!message || busy.value) return
  if ((session.value?.mode ?? mode.value) === 'najia' && !canUseNajia.value) {
    ElMessage.warning('请先在“六爻排盘”页面完成纳甲排盘。')
    return
  }
  const retry = pendingRetry.value?.kind === 'send' && pendingRetry.value.message === message
    ? pendingRetry.value
    : { kind: 'send' as const, message, requestId: crypto.randomUUID() }
  await runAction(retry)
}

async function regenerate(index: number) {
  if (!session.value || busy.value) return
  const generated = regenerateActionForAssistant(session.value.messages, index, crypto.randomUUID())
  if (!generated) return
  const retry = pendingRetry.value?.kind === 'regenerate'
    && pendingRetry.value.regenerateFromMessageId === generated.regenerateFromMessageId
    ? pendingRetry.value
    : generated
  await runAction(retry)
}

function retryLast() {
  if (pendingRetry.value) void runAction(pendingRetry.value)
}

function hasPersistedPendingFailure() {
  const requestId = pendingRetry.value?.requestId
  return Boolean(requestId && session.value?.failed_requests?.some((item) => item.request_id === requestId))
}

function retryFailedRequest(failed: AIFailedRequest) {
  const action = retryActionFromFailure(failed)
  pendingRetry.value = action
  if (action.kind === 'send') compose.value = action.message
  void runAction(action)
}

function stopGeneration() {
  controller?.abort()
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function formatVersions(value?: Record<string, unknown>) {
  return value ? Object.entries(value).map(([key, item]) => `${key}: ${typeof item === 'object' ? JSON.stringify(item) : item ?? '未提供'}`).join(' · ') : '旧会话未保存版本信息'
}

function isLatestMessage(index: number) {
  return Boolean(session.value && index === session.value.messages.length - 1)
}

watch(() => props.divination?.id, async () => {
  await refreshSettings()
  await loadSavedSessions()
  pendingRetry.value = null
}, { immediate: true })
</script>

<template>
  <section class="ai-page">
    <article v-if="divination" class="panel ai-context">
      <div class="section-heading">
        <div><span class="section-index">04</span><h2>当前卦象</h2></div>
        <span>{{ divination.base_hexagram.title }} → {{ divination.changed_hexagram.title }}</span>
      </div>
      <div class="ai-context__question"><span>当前占问</span><p>{{ divination.question }}</p></div>
      <div class="ai-context__meta"><span>起卦方式：{{ divination.method === 'coins' ? '三枚铜钱' : '手动输入' }}</span><span>动爻：{{ divination.moving_positions.length ? divination.moving_positions.join('、') : '无' }}</span></div>
      <small>AI 会话绑定本次卦象与规则版本快照；更换本卦、动爻或排盘后，请新建会话。</small>
    </article>

    <article class="panel ai-chat">
      <div class="section-heading">
        <div><span class="section-index">AI</span><h2>辅助解读</h2></div>
        <span class="ai-chat__model">{{ session?.model_id ?? settings?.model_id ?? '尚未选择模型' }}</span>
      </div>

      <div v-if="!settings?.ai_enabled" class="ai-notice">
        AI 尚未启用。请前往“设置”配置 DeepSeek API Key、选择当前可用模型并开启功能。起卦、经文和纳甲功能仍可独立使用。
        <el-button v-if="!divination" plain @click="emit('startCasting')">前往起卦</el-button>
      </div>
      <template v-else>
        <div v-if="sessions.length" class="ai-session-select">
          <label for="ai-session">已有会话</label>
          <el-select id="ai-session" :model-value="session?.id" placeholder="选择会话" @change="openSession">
            <el-option v-for="item in sessions" :key="item.id" :value="item.id" :label="`${item.mode === 'classical' ? '经文' : '纳甲'} · ${formatDate(item.created_at)} · ${item.model_id}`" />
          </el-select>
          <el-button text @click="startNewSession">新建会话</el-button>
        </div>

        <div class="ai-mode-row">
          <span>分析范围</span>
          <el-radio-group v-model="mode" :disabled="Boolean(session)">
            <el-radio-button value="classical">《周易》经文</el-radio-button>
            <el-radio-button value="najia" :disabled="!canUseNajia">六爻纳甲</el-radio-button>
          </el-radio-group>
          <small v-if="!canUseNajia">纳甲模式需先完成排盘并提供日月参数。</small>
        </div>
        <details v-if="session" class="ai-session-provenance">
          <summary>会话规则快照 · 查看技术版本</summary>
          <span>{{ formatVersions(session.rule_versions) }}</span>
        </details>

        <AIRequestStatus :phase="visiblePhase" :label="statusLabel" :help="statusHelp" :steps="progressSteps" />

        <div ref="messageList" class="ai-messages" aria-live="polite" :aria-busy="busy">
          <div v-if="!displayMessages.length && !busy" class="ai-empty">
            <span class="ai-empty__mark">易</span>
            <strong>{{ divination ? '还没有 AI 解读' : '先起一卦，再开始解读' }}</strong>
            <p>{{ divination ? '将发送当前卦象与本次消息；发送前会再次显示资料并征求确认。' : '起卦后可在此选择解读模式，并按需发送当前会话资料。' }}</p>
            <el-button v-if="divination" type="primary" :disabled="!ready" @click="sendMessage">开始解读</el-button>
            <el-button v-else plain @click="emit('startCasting')">前往起卦</el-button>
          </div>
          <AIMessage v-for="(item, index) in displayMessages" :key="item.id" :message="item" :can-regenerate="item.role === 'assistant' && isLatestMessage(index) && !busy" :status-label="statusHelp" @regenerate="regenerate(index)" />
          <div v-for="failed in session?.failed_requests ?? []" :key="failed.request_id" class="ai-failure-banner" role="status">
            <strong>上次请求未完成 · {{ aiFailureStageLabel(failed.stage) }} · {{ aiFailureTitle(failed.code) }}</strong>
            <span>{{ failed.message }}</span>
            <details><summary>查看详细信息</summary><code>技术错误码：{{ failed.code }} · 请求编号：{{ failed.request_id }}</code></details>
            <el-button plain type="warning" :disabled="busy" @click="retryFailedRequest(failed)">使用同一请求重试</el-button>
          </div>
          <div v-if="lastFailure" class="ai-failure-banner" role="status">
            <strong>{{ aiFailureStageLabel(lastFailure.stage) }} · {{ aiFailureTitle(lastFailure.code) }}</strong>
            <span>{{ lastFailure.message }}</span>
            <details><summary>查看详细信息</summary><code>技术错误码：{{ lastFailure.code }}</code></details>
          </div>
          <details v-if="showAIDiagnostics && diagnosticEvents.length" class="ai-diagnostics">
            <summary>前端诊断（仅开发版，脱敏）</summary>
            <ul><li v-for="(event, index) in diagnosticEvents" :key="index">{{ event.event }} · session={{ event.sessionId }} · message={{ event.messageId ?? '—' }} · request={{ event.requestId ?? '—' }} · {{ event.status }} · {{ event.contentType ?? '' }} · {{ event.messageCount ?? '' }} · {{ JSON.stringify(event.fields ?? {}) }}</li></ul>
          </details>
        </div>
        <div v-if="pendingRetry && !busy && !hasPersistedPendingFailure()" class="ai-retry-banner">
          <span>本次请求未完成；问题、会话上下文和请求编号已保留。重试前仍会显示外发确认。</span>
          <el-button plain type="warning" @click="retryLast">重试上次请求</el-button>
        </div>
        <form class="ai-composer" @submit.prevent="sendMessage">
          <label for="ai-compose">发送消息</label>
          <el-input id="ai-compose" v-model="compose" type="textarea" :rows="3" maxlength="2000" show-word-limit resize="vertical" :disabled="busy || !divination?.id" placeholder="围绕当前卦象继续追问……" />
          <div><span>每次发送前会再次确认资料；只带入当前会话，不读取其他历史。</span>
            <el-button v-if="busy" plain type="danger" @click="stopGeneration">停止生成</el-button>
            <el-button v-else type="primary" :disabled="!ready || !divination?.id" @click="sendMessage">发送</el-button>
          </div>
        </form>
      </template>
    </article>
  </section>
</template>
