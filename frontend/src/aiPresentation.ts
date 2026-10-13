export type AIRequestPhase = 'waiting' | 'connecting' | 'thinking' | 'generating' | 'complete' | 'failed' | 'cancelled'

export interface AIProgressStep {
  label: string
  done: boolean
  active: boolean
  failed: boolean
}

export function aiPhaseLabel(phase: AIRequestPhase): string {
  return ({
    waiting: '等待生成', connecting: '正在连接', thinking: '模型正在思考',
    generating: '正在生成', complete: '已完成', failed: '请求未完成', cancelled: '已取消',
  })[phase]
}

export function aiPhaseHelp(phase: AIRequestPhase, ready: boolean, streamedCharacters: number): string {
  if (phase === 'connecting') return '正在连接模型服务…'
  if (phase === 'thinking') return '模型正在整理思路；内部过程内容默认折叠。'
  if (phase === 'generating') return `正在生成最终解读… 已接收 ${streamedCharacters} 个待校验字符。生成完成后，服务端会校验并保存。`
  if (phase === 'complete') return '最终回答已通过校验并保存在本机。'
  if (phase === 'failed') return '本次回答未完成。请查看失败阶段和原因；你可以在确认后主动重试。'
  if (phase === 'cancelled') return '生成已停止；未完成的回答不会当作正式解读。'
  return ready ? '首次发送前会显示将发送的资料并征求确认。' : '先保存一次起卦记录并启用 AI。'
}

export function aiProgressSteps(phase: AIRequestPhase, failureStage?: string): AIProgressStep[] {
  const failureIndex = failureStage === 'validation' ? 2
    : failureStage === 'persistence' ? 3
      : failureStage === 'generation' || failureStage === 'transport' ? 1 : 0
  return [
    { label: '连接', done: ['thinking', 'generating', 'complete'].includes(phase), active: phase === 'connecting', failed: phase === 'failed' && failureIndex === 0 },
    { label: '生成', done: phase === 'complete', active: phase === 'thinking' || phase === 'generating', failed: phase === 'failed' && failureIndex === 1 },
    { label: '校验', done: phase === 'complete', active: false, failed: phase === 'failed' && failureIndex === 2 },
    { label: '保存', done: phase === 'complete', active: false, failed: phase === 'failed' && failureIndex === 3 },
  ]
}

export function aiFailureStageLabel(stage: string): string {
  const labels: Record<string, string> = {
    generation: '生成阶段', validation: '内容校验阶段', persistence: '保存阶段',
    transport: '连接阶段', configuration: '配置阶段', processing: '处理阶段',
    cancelled: '已停止', refresh: '会话刷新', unknown: '请求阶段',
  }
  return labels[stage] ?? stage
}

export function aiFailureTitle(code: string): string {
  const labels: Record<string, string> = {
    invalid_json: '回答格式无法解析', invalid_schema: '回答结构不完整',
    duplicate_evidence_id: '引用了重复的本地证据', invalid_evidence_id: '引用超出当前会话资料',
    missing_local_evidence: '本地典籍资料缺少可展示原文', output_truncated: '回答因长度限制未完成',
    generation_incomplete: '模型未能完整结束生成', missing_finish_reason: '未收到生成完成状态',
    empty_final_content: '模型没有返回最终解读', provider_timeout: '连接模型超时',
    provider_disconnected: '与模型的连接中断', stream_incomplete: '生成连接提前结束',
    persistence_failed: '回答未能保存到本机', persistence_conflict: '保存确认发生冲突',
    generation_cancelled: '用户已停止生成', session_refresh_failed: '会话刷新失败',
  }
  return labels[code] ?? '本次请求未完成'
}
