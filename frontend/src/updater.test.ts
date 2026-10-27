import { describe, expect, it, vi } from 'vitest'
import { createUpdater, formatBytes, formatDuration, formatSpeed, type RemoteUpdate, type UpdaterDeps } from './updater'

function memoryStorage(seed: Record<string, string> = {}) {
  const data = new Map(Object.entries(seed))
  return {
    getItem: (key: string) => (data.has(key) ? (data.get(key) as string) : null),
    setItem: (key: string, value: string) => void data.set(key, value),
    dump: () => Object.fromEntries(data),
  }
}

function remoteUpdate(overrides: Partial<RemoteUpdate> = {}): RemoteUpdate {
  return {
    version: '3.3.3',
    currentVersion: '3.3.2',
    date: '2026-11-02T00:00:00Z',
    body: '修复若干问题',
    download: vi.fn(async (onEvent) => {
      onEvent({ event: 'Started', data: { contentLength: 1000 } })
      onEvent({ event: 'Progress', data: { chunkLength: 400 } })
      onEvent({ event: 'Progress', data: { chunkLength: 600 } })
      onEvent({ event: 'Finished' })
    }),
    install: vi.fn(async () => {}),
    close: vi.fn(async () => {}),
    ...overrides,
  }
}

function deps(overrides: Partial<UpdaterDeps> = {}): UpdaterDeps {
  return {
    isDesktop: () => true,
    getVersion: async () => '3.3.2',
    checkUpdate: async () => null,
    relaunch: vi.fn(async () => {}),
    prepareForUpdate: vi.fn(async () => ({ stopped: true })),
    backupDatabase: vi.fn(async () => ({ path: '/tmp/backup.sqlite3', bytes: 2048, historyCount: 7 })),
    now: () => 1_700_000_000_000,
    storage: memoryStorage(),
    ...overrides,
  }
}

describe('updater state machine', () => {
  it('浏览器环境保持 unsupported，绝不调用原生接口', async () => {
    const checkUpdate = vi.fn(async () => remoteUpdate())
    const store = createUpdater(deps({ isDesktop: () => false, checkUpdate }))
    await store.init()
    await store.check({ manual: true })
    expect(store.state.phase).toBe('unsupported')
    expect(checkUpdate).not.toHaveBeenCalled()
  })

  it('已是最新版本时给出 up_to_date', async () => {
    const store = createUpdater(deps({ checkUpdate: async () => null }))
    await store.init()
    await store.check({ manual: true })
    expect(store.state.phase).toBe('up_to_date')
    expect(store.state.latest).toBeNull()
  })

  it('发现新版本只报告，不下载不安装', async () => {
    const update = remoteUpdate()
    const store = createUpdater(deps({ checkUpdate: async () => update }))
    await store.init()
    await store.check({ manual: true })
    expect(store.state.phase).toBe('available')
    expect(store.state.latest?.version).toBe('3.3.3')
    expect(update.download).not.toHaveBeenCalled()
    expect(update.install).not.toHaveBeenCalled()
  })

  it('“稍后”保留版本信息但不下载', async () => {
    const update = remoteUpdate()
    const store = createUpdater(deps({ checkUpdate: async () => update }))
    await store.init()
    await store.check({ manual: true })
    store.defer()
    expect(store.state.phase).toBe('deferred')
    expect(store.state.latest?.version).toBe('3.3.3')
    expect(update.download).not.toHaveBeenCalled()
  })

  it('下载 → 备份 → 停服务 → 安装 → 重启 的顺序正确，并统计真实进度', async () => {
    const calls: string[] = []
    const update = remoteUpdate({
      download: vi.fn(async (onEvent) => {
        calls.push('download')
        onEvent({ event: 'Started', data: { contentLength: 1000 } })
        onEvent({ event: 'Progress', data: { chunkLength: 250 } })
        onEvent({ event: 'Progress', data: { chunkLength: 750 } })
        onEvent({ event: 'Finished' })
      }),
      install: vi.fn(async () => {
        calls.push('install')
      }),
    })
    const store = createUpdater(
      deps({
        checkUpdate: async () => update,
        backupDatabase: vi.fn(async () => {
          calls.push('backup')
          return { path: '/tmp/b', bytes: 10 }
        }),
        prepareForUpdate: vi.fn(async () => {
          calls.push('prepare')
          return { stopped: true }
        }),
        relaunch: vi.fn(async () => {
          calls.push('relaunch')
        }),
      }),
    )
    await store.init()
    await store.check({ manual: true })
    await store.downloadAndInstall()

    expect(calls).toEqual(['download', 'backup', 'prepare', 'install', 'relaunch'])
    expect(store.state.phase).toBe('completed')
    expect(store.state.progress.received).toBe(1000)
    expect(store.state.progress.percent).toBe(100)
  })

  it('备份失败时取消安装，且不停服务', async () => {
    const update = remoteUpdate()
    const prepareForUpdate = vi.fn(async () => ({ stopped: true }))
    const store = createUpdater(
      deps({
        checkUpdate: async () => update,
        backupDatabase: async () => {
          throw new Error('磁盘已满')
        },
        prepareForUpdate,
      }),
    )
    await store.init()
    await store.check({ manual: true })
    await store.downloadAndInstall()
    expect(update.install).not.toHaveBeenCalled()
    expect(prepareForUpdate).not.toHaveBeenCalled()
    expect(store.state.phase).toBe('error')
    expect(store.state.error).toContain('备份失败')
  })

  it('本地服务未能停止时取消安装', async () => {
    const update = remoteUpdate()
    const store = createUpdater(
      deps({
        checkUpdate: async () => update,
        prepareForUpdate: async () => ({ stopped: false }),
      }),
    )
    await store.init()
    await store.check({ manual: true })
    await store.downloadAndInstall()
    expect(update.install).not.toHaveBeenCalled()
    expect(store.state.phase).toBe('error')
    expect(store.state.error).toContain('未能停止')
  })

  it('重复点击不会产生并发检查', async () => {
    let release: (value: RemoteUpdate | null) => void = () => {}
    const pending = new Promise<RemoteUpdate | null>((resolve) => {
      release = resolve
    })
    const checkUpdate = vi.fn(() => pending)
    const store = createUpdater(deps({ checkUpdate }))
    const first = store.check({ manual: true })
    const second = store.check({ manual: true })
    release(null)
    await Promise.all([first, second])
    expect(checkUpdate).toHaveBeenCalledTimes(1)
  })

  it('下载过程中再次点击安装会被忽略', async () => {
    const update = remoteUpdate({
      download: vi.fn(async (onEvent) => {
        await new Promise((resolve) => setTimeout(resolve, 20))
        onEvent({ event: 'Finished' })
      }),
    })
    const store = createUpdater(deps({ checkUpdate: async () => update }))
    await store.init()
    await store.check({ manual: true })
    const first = store.downloadAndInstall()
    const second = store.downloadAndInstall()
    await Promise.all([first, second])
    expect(update.download).toHaveBeenCalledTimes(1)
    expect(update.install).toHaveBeenCalledTimes(1)
  })

  it('网络超时归类为 offline，并保留可重试的提示', async () => {
    const original = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(navigator), 'onLine')
    Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => true })
    try {
      const store = createUpdater(
        deps({
          checkUpdate: async () => {
            throw new Error('error sending request for url: connection timed out')
          },
        }),
      )
      await store.init()
      await store.check({ manual: true })
      expect(store.state.phase).toBe('offline')
      expect(store.state.error).toContain('更新服务')
    } finally {
      if (original) Object.defineProperty(Object.getPrototypeOf(navigator), 'onLine', original)
    }
  })

  it('系统报告离线时不发起请求也不误报为已是最新', async () => {
    const original = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(navigator), 'onLine')
    Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => false })
    try {
      const store = createUpdater(
        deps({
          checkUpdate: async () => {
            throw new Error('fetch failed')
          },
        }),
      )
      await store.init()
      await store.check({ manual: true })
      expect(store.state.phase).toBe('offline')
      expect(store.state.error).toContain('离线')
    } finally {
      if (original) Object.defineProperty(Object.getPrototypeOf(navigator), 'onLine', original)
    }
  })

  it('24 小时内不重复自动检查；关闭自动检查后完全不查', async () => {
    const storage = memoryStorage({ 'yijing.update.lastCheck': String(1_700_000_000_000 - 1000) })
    const checkUpdate = vi.fn(async () => null)
    const store = createUpdater(deps({ checkUpdate, storage }))
    await store.init()
    expect(checkUpdate).not.toHaveBeenCalled()

    const offlineStorage = memoryStorage({ 'yijing.update.auto': 'false' })
    const offlineCheck = vi.fn(async () => null)
    const disabled = createUpdater(deps({ checkUpdate: offlineCheck, storage: offlineStorage }))
    await disabled.init()
    expect(offlineCheck).not.toHaveBeenCalled()
  })

  it('超过 24 小时后自动检查一次并记录时间', async () => {
    const storage = memoryStorage({ 'yijing.update.lastCheck': String(1_700_000_000_000 - 25 * 60 * 60 * 1000) })
    const checkUpdate = vi.fn(async () => null)
    const store = createUpdater(deps({ checkUpdate, storage }))
    await store.init()
    expect(checkUpdate).toHaveBeenCalledTimes(1)
    expect(storage.dump()['yijing.update.lastCheck']).toBe('1700000000000')
  })

  it('自动检查开关持久化', () => {
    const storage = memoryStorage()
    const store = createUpdater(deps({ storage }))
    expect(store.state.autoCheck).toBe(true)
    store.setAutoCheck(false)
    expect(store.state.autoCheck).toBe(false)
    expect(storage.dump()['yijing.update.auto']).toBe('false')
  })
})

describe('updater formatting', () => {
  it('字节、速度、时长都给出可读值', () => {
    expect(formatBytes(0)).toBe('—')
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(1536)).toBe('1.5 KiB')
    expect(formatBytes(16_097_113)).toBe('15.4 MiB')
    expect(formatSpeed(1024 * 1024)).toBe('1.0 MiB/s')
    expect(formatSpeed(0)).toBe('—')
    expect(formatDuration(1500)).toBe('2 秒')
    expect(formatDuration(92_000)).toBe('1 分 32 秒')
    expect(formatDuration(0)).toBe('—')
  })
})
