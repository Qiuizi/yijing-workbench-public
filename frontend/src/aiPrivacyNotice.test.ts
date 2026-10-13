import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { confirmMock } = vi.hoisted(() => ({ confirmMock: vi.fn() }))

vi.mock('element-plus', () => ({ ElMessageBox: { confirm: confirmMock } }))

import { requireAIPrivacyAcknowledgement } from './aiPrivacyNotice'

function createMemoryStorage() {
  const values = new Map<string, string>()
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  }
}

describe('DeepSeek privacy acknowledgement', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', createMemoryStorage())
    confirmMock.mockReset()
  })

  afterEach(() => vi.unstubAllGlobals())

  it('stores a confirmed acknowledgement and does not prompt again', async () => {
    confirmMock.mockResolvedValue(undefined)

    expect(await requireAIPrivacyAcknowledgement()).toBe(true)
    expect(globalThis.localStorage.getItem('yijing.ai-network-privacy.v1')).toBe('accepted')
    expect(await requireAIPrivacyAcknowledgement()).toBe(true)
    expect(confirmMock).toHaveBeenCalledTimes(1)
  })

  it('does not allow a provider request when the notice is declined', async () => {
    confirmMock.mockRejectedValue('cancel')

    expect(await requireAIPrivacyAcknowledgement()).toBe(false)
    expect(globalThis.localStorage.getItem('yijing.ai-network-privacy.v1')).toBeNull()
  })
})
