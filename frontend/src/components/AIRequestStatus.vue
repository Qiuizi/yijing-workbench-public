<script setup lang="ts">
import type { AIProgressStep, AIRequestPhase } from '../aiPresentation'

defineProps<{
  phase: AIRequestPhase
  label: string
  help: string
  steps: AIProgressStep[]
}>()
</script>

<template>
  <div class="ai-progress" :data-state="phase" role="status" aria-live="polite">
    <div class="ai-progress__heading"><span class="ai-progress__indicator"></span><strong>{{ label }}</strong><p>{{ help }}</p></div>
    <ol class="ai-progress__steps" aria-label="AI 请求处理阶段">
      <li v-for="(step, index) in steps" :key="step.label" :class="{ 'is-done': step.done, 'is-active': step.active, 'is-failed': step.failed }" :aria-current="step.active ? 'step' : undefined">
        <span>{{ index + 1 }}</span><strong>{{ step.label }}</strong>
      </li>
    </ol>
  </div>
</template>
