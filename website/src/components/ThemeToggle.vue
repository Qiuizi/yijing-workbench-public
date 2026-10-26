<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '../theme'

const props = defineProps<{ labelToDark: string; labelToLight: string }>()
const { isDark, toggle } = useTheme()
const label = computed(() => (isDark.value ? props.labelToLight : props.labelToDark))
</script>

<template>
  <button
    class="theme-toggle"
    type="button"
    :aria-label="label"
    :title="label"
    :aria-pressed="isDark ? 'true' : 'false'"
    @click="toggle"
  >
    <svg v-if="isDark" class="theme-toggle__icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="10" cy="10" r="3.6" stroke="currentColor" stroke-width="1.4" />
      <g stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
        <path d="M10 2.4v1.8M10 15.8v1.8M2.4 10h1.8M15.8 10h1.8M4.6 4.6l1.3 1.3M14.1 14.1l1.3 1.3M15.4 4.6l-1.3 1.3M5.9 14.1l-1.3 1.3" />
      </g>
    </svg>
    <svg v-else class="theme-toggle__icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M16.2 12.4A6.8 6.8 0 0 1 7.6 3.8a6.9 6.9 0 1 0 8.6 8.6Z"
        stroke="currentColor"
        stroke-width="1.4"
        stroke-linejoin="round"
      />
    </svg>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  color: var(--text-2);
  background: transparent;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    color var(--dur-1) var(--ease-out),
    border-color var(--dur-1) var(--ease-out),
    background-color var(--dur-1) var(--ease-out);
}
.theme-toggle:hover { color: var(--accent); border-color: var(--accent-line); background: var(--accent-soft); }
.theme-toggle:active { transform: translateY(0.5px); }
.theme-toggle__icon { width: 17px; height: 17px; transition: transform var(--dur-3) var(--ease-out); }
.theme-toggle:hover .theme-toggle__icon { transform: rotate(-12deg); }
</style>
