import { computed, ref } from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'yijing-theme'

function readStored(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

function prefersDark(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
}

function currentDocumentTheme(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

// 单例状态：页头按钮与首屏脚本共用同一份主题。
const stored = ref<Theme | null>(readStored())
const theme = ref<Theme>(
  typeof document === 'undefined' ? 'light' : currentDocumentTheme(),
)

function apply(next: Theme) {
  theme.value = next
  document.documentElement.dataset.theme = next
  const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
  if (meta) meta.content = next === 'dark' ? '#131c17' : '#f8f4ea'
}

export function useTheme() {
  const isDark = computed(() => theme.value === 'dark')

  function toggle() {
    const next: Theme = theme.value === 'dark' ? 'light' : 'dark'
    stored.value = next
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* 隐私模式下忽略写入失败，仅本次生效 */
    }
    apply(next)
  }

  // 用户没有手动选择时跟随系统；选择过就以用户为准。
  if (typeof window !== 'undefined' && !stored.value) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
      if (!stored.value) apply(event.matches ? 'dark' : 'light')
    })
  }

  return { theme, isDark, toggle }
}

// 供内联脚本之外的首屏兜底：若 HTML 未注入 data-theme，这里补一次。
export function ensureThemeApplied() {
  if (typeof document === 'undefined') return
  const next: Theme = stored.value ?? (prefersDark() ? 'dark' : 'light')
  apply(next)
}
