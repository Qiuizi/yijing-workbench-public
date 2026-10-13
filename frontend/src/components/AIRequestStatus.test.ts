import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import AIRequestStatus from './AIRequestStatus.vue'
import { aiFailureStageLabel, aiFailureTitle, aiPhaseHelp, aiPhaseLabel, aiProgressSteps, type AIRequestPhase } from '../aiPresentation'

async function render(phase: AIRequestPhase, failureStage?: string) {
  return renderToString(createSSRApp(AIRequestStatus, {
    phase,
    label: aiPhaseLabel(phase),
    help: aiPhaseHelp(phase, true, 12),
    steps: aiProgressSteps(phase, failureStage),
  }))
}

describe('AI request status presentation', () => {
  it('shows a clear waiting state', async () => {
    const html = await render('waiting')
    expect(html).toContain('等待生成')
    expect(html).toContain('首次发送前会显示将发送的资料并征求确认。')
    expect(html).toContain('role="status"')
  })

  it('shows thinking and streaming progress without claiming validation is complete', async () => {
    const thinking = await render('thinking')
    const generating = await render('generating')
    expect(thinking).toContain('模型正在思考')
    expect(generating).toContain('正在生成最终解读')
    expect(generating).toContain('已接收 12 个待校验字符')
    expect(generating).not.toContain('最终回答已通过校验')
  })

  it('marks verified completion and the failed stage distinctly', async () => {
    const complete = await render('complete')
    const failed = await render('failed', 'validation')
    expect(complete).toContain('最终回答已通过校验并保存在本机。')
    expect(complete.match(/class="[^"]*is-done/g)?.length).toBe(4)
    expect(failed).toContain('请求未完成')
    expect(failed).toContain('is-failed')
    expect(failed).toContain('校验')
  })

  it('distinguishes user cancellation from failure', async () => {
    const html = await render('cancelled')
    expect(html).toContain('生成已停止')
    expect(html).not.toContain('请求未完成')
  })

  it('maps validation errors to a readable stage and title without exposing internal codes', () => {
    expect(aiFailureStageLabel('validation')).toBe('内容校验阶段')
    expect(aiFailureTitle('invalid_evidence_id')).toBe('引用超出当前会话资料')
    expect(aiFailureTitle('invalid_evidence_id')).not.toContain('invalid_evidence_id')
  })
})
