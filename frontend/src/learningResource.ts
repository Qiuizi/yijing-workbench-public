import { onScopeDispose, ref, shallowRef } from 'vue'
import type { Hexagram } from './types'

/** Shared by the preview and reader; coalesce clicks while a preview is loading. */
export function createHexagramCache(load: (id: number) => Promise<Hexagram>) {
  const cache = new Map<number, Hexagram>()
  const pending = new Map<number, Promise<Hexagram>>()
  return (id: number): Promise<Hexagram> => {
    const saved = cache.get(id)
    if (saved) return Promise.resolve(saved)
    const existing = pending.get(id)
    if (existing) return existing
    const request = Promise.resolve()
      .then(() => load(id))
      .then((entry) => {
        cache.set(id, entry)
        return entry
      })
      .finally(() => pending.delete(id))
    pending.set(id, request)
    return request
  }
}

/** A stale preview or detail response can populate the cache, never the current UI. */
export function useLearningResource(load: (id: number) => Promise<Hexagram>) {
  const entry = shallowRef<Hexagram | null>(null)
  const loading = ref(false)
  const error = ref('')
  let version = 0
  function reset() {
    version++
    entry.value = null
    loading.value = false
    error.value = ''
  }
  async function read(id: number) {
    const request = ++version
    entry.value = null
    error.value = ''
    loading.value = true
    try {
      const result = await load(id)
      if (request === version) entry.value = result
    } catch (reason) {
      if (request === version)
        error.value =
          reason instanceof Error ? reason.message : '资料读取失败，请重试。'
    } finally {
      if (request === version) loading.value = false
    }
  }
  onScopeDispose(reset)
  return { entry, loading, error, read, reset }
}
