<script setup lang="ts">
import type { AIAssistantMessageView, AIMessageView } from '../aiMessageModel'

defineProps<{
  message: AIMessageView
  canRegenerate?: boolean
  statusLabel?: string
}>()

const emit = defineEmits<{ regenerate: [] }>()

function evidenceExplanations(message: AIAssistantMessageView) {
  return Array.isArray(message.result?.traditional_basis) ? message.result.traditional_basis : []
}

function legacyBasis(message: AIAssistantMessageView) {
  return typeof message.result?.traditional_basis === 'string' ? message.result.traditional_basis : ''
}

function evidenceLabel(message: AIAssistantMessageView, id: string) {
  return message.result?.cited_passages?.find((item) => item.id === id)?.label ?? `本地证据 ${id}`
}
</script>

<template>
  <article class="ai-message" :class="`ai-message--${message.role}`" :data-status="message.status">
    <template v-if="message.role === 'user'">
      <span class="ai-message__role">你</span><p>{{ message.content }}</p>
    </template>
    <template v-else-if="message.status === 'streaming'">
      <span class="ai-message__role">AI 辅助说明 · {{ message.model }}</span>
      <p>{{ statusLabel ?? '正在处理本次请求…' }}<span v-if="message.content"> {{ message.content }}</span></p>
      <details v-if="message.reasoningPreview" class="ai-reasoning">
        <summary>查看推理过程</summary>
        <p>这是模型内部分析过程，不属于最终解读。</p>
        <pre>{{ message.reasoningPreview }}</pre>
      </details>
    </template>
    <template v-else>
      <span class="ai-message__role">AI 辅助说明 · {{ message.model ?? message.result?.provider?.model_id ?? '已保存回答' }}</span>
      <template v-if="message.result">
        <section class="ai-answer-section ai-answer-section--overview">
          <h3>卦象概述</h3><p>{{ message.result.overview || '本次回答未提供概述。' }}</p>
        </section>

        <section class="ai-answer-section">
          <h3>典籍依据 <span class="ai-section-source">本地典籍资料</span></h3>
          <div v-if="message.result.cited_passages?.length" class="ai-citations">
            <blockquote v-for="passage in message.result.cited_passages" :key="passage.id">
              <div><strong>{{ passage.label }}</strong><span>本地核验原文</span></div>
              <p>{{ passage.text }}</p>
              <a :href="passage.source_url" target="_blank" rel="noreferrer">维基文库固定版本 <span v-if="passage.source_revision_id">#{{ passage.source_revision_id }}</span></a>
            </blockquote>
          </div>
          <p v-else class="ai-answer-section__empty">本次回答未引用本地典籍段落。</p>
          <div v-if="message.result.cited_rules?.length" class="ai-citations ai-citations--rules">
            <blockquote v-for="rule in message.result.cited_rules" :key="rule.id">
              <div><strong>{{ rule.name }}</strong><span>本地规则资料</span></div>
              <p>{{ rule.rule_scope }}</p>
              <a v-if="rule.source_url" :href="rule.source_url" target="_blank" rel="noreferrer">{{ rule.source_title }}<span v-if="rule.source_revision_id"> · 修订 {{ rule.source_revision_id }}</span></a>
            </blockquote>
          </div>
        </section>

        <section class="ai-answer-section ai-answer-section--basis">
          <h3>AI 对传统依据的说明</h3>
          <div v-if="evidenceExplanations(message).length" class="ai-evidence-explanations">
            <article v-for="basis in evidenceExplanations(message)" :key="basis.evidence_id">
              <strong>{{ evidenceLabel(message, basis.evidence_id) }}</strong><p>{{ basis.explanation }}</p>
            </article>
          </div>
          <p v-else>{{ legacyBasis(message) || '本次回答未提供传统依据说明。' }}</p>
        </section>

        <section class="ai-answer-section ai-answer-section--modern">
          <h3>结合问题的分析 <span class="ai-section-generated">模型生成</span></h3>
          <p>{{ message.result.modern_interpretation || '本次回答未提供结合问题的分析。' }}</p>
        </section>

        <section class="ai-answer-section ai-answer-section--suggestions">
          <h3>可以考虑的方向</h3>
          <ul v-if="message.result.suggestions?.length"><li v-for="(suggestion, index) in message.result.suggestions" :key="index">{{ suggestion }}</li></ul>
          <p v-else class="ai-answer-section__empty">本次回答未提供具体建议。</p>
        </section>

        <p class="ai-message__caution">{{ message.result.caution || 'AI 内容仅供整理思路，不构成对未来的确定判断。' }}</p>
        <details class="ai-message__metadata">
          <summary>模型、规则与用量信息</summary>
          <div>
            <span>响应格式：{{ message.result.response_schema ?? '旧版兼容格式' }}</span>
            <span>规则：{{ message.result.ruleset?.name ?? '旧会话' }} {{ message.result.ruleset?.version ?? '' }} · {{ message.result.mode === 'classical' ? '经文模式' : '纳甲模式' }}</span>
            <span v-if="message.result.provider">模型：{{ message.result.provider.model_id }}</span>
            <span v-if="message.result.provider?.usage">Token：输入 {{ message.result.provider.usage.prompt_tokens }} · 输出 {{ message.result.provider.usage.completion_tokens }}</span>
            <span v-if="message.result.provider?.cost_estimate">估算费用：${{ message.result.provider.cost_estimate.off_peak }}–${{ message.result.provider.cost_estimate.peak }} USD（低峰–高峰）</span>
            <span v-else-if="message.result.provider?.usage">此模型无本地核验价格表，未估算费用。</span>
            <a v-if="message.result.provider?.pricing_source_url" :href="message.result.provider.pricing_source_url" target="_blank" rel="noreferrer">价格依据 · {{ message.result.provider.pricing_checked_at }}</a>
          </div>
        </details>
      </template>
      <p v-else class="ai-message__unparsed">{{ message.content || '已保存 assistant 消息，但当前版本无法解析其展示格式。原记录仍保留。' }}</p>
      <button v-if="canRegenerate" class="ai-message__regenerate" type="button" @click="emit('regenerate')">重新生成</button>
    </template>
  </article>
</template>
