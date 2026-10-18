import { computed, onMounted, onUnmounted, ref } from 'vue'
export type Page = 'divination' | 'learning' | 'history' | 'settings'
export function parseRoute(hash: string): {
  page: Page
  hexagramId: number | null
} {
  const match = /^#\/(divination|learning|history|settings)(?:\/(\d+))?$/.exec(
    hash,
  )
  if (!match) return { page: 'divination', hexagramId: null }
  const id = Number(match[2])
  return {
    page: match[1] as Page,
    hexagramId:
      match[1] === 'learning' && Number.isInteger(id) && id >= 1 && id <= 64
        ? id
        : null,
  }
}
export function useNavigation() {
  const hash = ref(typeof window === 'undefined' ? '' : window.location.hash)
  const sync = () => {
    hash.value = window.location.hash
  }
  onMounted(() => window.addEventListener('hashchange', sync))
  onUnmounted(() => window.removeEventListener('hashchange', sync))
  function navigate(page: Page, id?: number) {
    window.location.hash = `/${page}${id ? `/${id}` : ''}`
    sync()
  }
  const route = computed(() => parseRoute(hash.value))
  return { route, navigate }
}
