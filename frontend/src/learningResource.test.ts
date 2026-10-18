import { effectScope } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createHexagramCache, useLearningResource } from './learningResource'
import type { Hexagram } from './types'
const scopes: ReturnType<typeof effectScope>[] = []
function resource(load: (id: number) => Promise<Hexagram>) {
  const scope = effectScope()
  scopes.push(scope)
  return { scope, state: scope.run(() => useLearningResource(load))! }
}
function deferred() {
  let resolve!: (entry: Hexagram) => void
  let reject!: (error: Error) => void
  const promise = new Promise<Hexagram>((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}
const entry = (id: number) =>
  ({ wenwang_order: id, judgment: `原文 ${id}` }) as Hexagram
afterEach(() => scopes.splice(0).forEach((scope) => scope.stop()))
describe('read-only learning preview and detail resources', () => {
  it('shares pending preview/detail requests, caches success, and retries failures', async () => {
    const request = deferred()
    const loader = vi
      .fn()
      .mockReturnValueOnce(request.promise)
      .mockRejectedValueOnce(new Error('暂时失败'))
      .mockResolvedValue(entry(2))
    const get = createHexagramCache(loader)
    const preview = get(1),
      detail = get(1)
    expect(preview).toBe(detail)
    await Promise.resolve()
    expect(loader).toHaveBeenCalledTimes(1)
    request.resolve(entry(1))
    await expect(detail).resolves.toMatchObject({ wenwang_order: 1 })
    await get(1)
    expect(loader).toHaveBeenCalledTimes(1)
    await expect(get(2)).rejects.toThrow('暂时失败')
    await expect(get(2)).resolves.toMatchObject({ wenwang_order: 2 })
    expect(loader).toHaveBeenCalledTimes(3)
  })
  it('never shows old text under a newly selected hexagram or overwrites it with stale success', async () => {
    const old = deferred(),
      current = deferred()
    const loader = vi
      .fn()
      .mockReturnValueOnce(old.promise)
      .mockReturnValueOnce(current.promise)
    const { state } = resource(loader)
    const first = state.read(1),
      second = state.read(2)
    expect(state.entry.value).toBeNull()
    current.resolve(entry(2))
    await second
    old.resolve(entry(1))
    await first
    expect(state.entry.value?.wenwang_order).toBe(2)
    expect(state.loading.value).toBe(false)
    expect(state.error.value).toBe('')
  })
  it('ignores stale errors and invalidates reads when leaving or disposing the page', async () => {
    const old = deferred(),
      pending = deferred()
    const loader = vi
      .fn()
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce(entry(2))
      .mockReturnValueOnce(pending.promise)
    const { state, scope } = resource(loader)
    const first = state.read(1)
    await state.read(2)
    old.reject(new Error('旧请求错误'))
    await first
    expect(state.error.value).toBe('')
    const last = state.read(3)
    scope.stop()
    pending.resolve(entry(3))
    await last
    expect(state.entry.value).toBeNull()
    expect(state.loading.value).toBe(false)
  })
  it('reports the current failure and can recover without leaking previous content', async () => {
    const loader = vi
      .fn()
      .mockResolvedValueOnce(entry(1))
      .mockRejectedValueOnce(new Error('无法读取'))
      .mockResolvedValueOnce(entry(2))
    const { state } = resource(loader)
    await state.read(1)
    await state.read(2)
    expect(state.entry.value).toBeNull()
    expect(state.error.value).toBe('无法读取')
    await state.read(2)
    expect(state.entry.value?.wenwang_order).toBe(2)
    expect(state.error.value).toBe('')
  })
})
