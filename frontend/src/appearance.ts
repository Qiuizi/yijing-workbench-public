import { computed, ref } from 'vue'

export type Appearance = 'auto' | 'light' | 'dark'

const STORAGE_KEY = 'yijing-appearance'

function readStored(): Appearance {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' || value === 'auto' ? value : 'auto'
  } catch {
    return 'auto'
  }
}

const query =
  typeof window !== 'undefined' ? window.matchMedia('(prefers-color-scheme: dark)') : null

const mode = ref<Appearance>(readStored())
const systemDark = ref(query?.matches ?? false)

const resolved = computed<'light' | 'dark'>(() =>
  mode.value === 'auto' ? (systemDark.value ? 'dark' : 'light') : mode.value,
)

function paint() {
  const root = document.documentElement
  // 同时写 data-theme（我们的 token）与 .dark（Element Plus 暗色变量入口）
  root.dataset.theme = resolved.value
  root.classList.toggle('dark', resolved.value === 'dark')
  root.style.colorScheme = resolved.value
}

function setMode(next: Appearance) {
  mode.value = next
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    /* 无痕模式下仅本次生效 */
  }
  paint()
}

export function initAppearance() {
  if (typeof document === 'undefined') return
  query?.addEventListener('change', (event) => {
    systemDark.value = event.matches
    if (mode.value === 'auto') paint()
  })
  paint()
}

export function useAppearance() {
  return { mode, resolved, setMode }
}
