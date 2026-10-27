/**
 * 应用内更新：状态机 + 数据保全 + 进度/错误处理。
 *
 * 设计约束（与 docs/updater/README.md 对应）：
 * 1. 只在真实 Tauri 桌面环境启用；浏览器里一律 unsupported，绝不调用原生接口。
 * 2. 不静默安装：check 只报告；下载与安装必须由用户点击触发。
 * 3. 安装前先做 SQLite 一致性备份，再停 sidecar，最后交给官方 updater 安装。
 * 4. 同一时间只允许一个检查/下载/安装任务（busy 守卫）。
 * 5. 依赖全部注入，便于在不启动 Tauri 的情况下做单元测试。
 */
import { computed, reactive, readonly } from 'vue'

export type UpdatePhase =
  | 'unsupported'
  | 'idle'
  | 'checking'
  | 'up_to_date'
  | 'available'
  | 'deferred'
  | 'downloading'
  | 'installing'
  | 'completed'
  | 'offline'
  | 'error'

export interface UpdateDownloadEvent {
  event: 'Started' | 'Progress' | 'Finished'
  data?: { contentLength?: number; chunkLength?: number }
}

export interface RemoteUpdate {
  version: string
  currentVersion: string
  date?: string
  body?: string
  download: (onEvent: (event: UpdateDownloadEvent) => void) => Promise<void>
  install: () => Promise<void>
  close?: () => Promise<void>
}

export interface UpdatePreparation {
  stopped: boolean
  appVersion?: string
  dataDir?: string
  databasePath?: string
}

export interface UpdateBackup {
  path?: string
  bytes?: number
  historyCount?: number
}

export interface UpdaterDeps {
  isDesktop: () => boolean
  getVersion: () => Promise<string>
  checkUpdate: () => Promise<RemoteUpdate | null>
  relaunch: () => Promise<void>
  prepareForUpdate: () => Promise<UpdatePreparation>
  backupDatabase: () => Promise<UpdateBackup>
  now?: () => number
  storage?: Pick<Storage, 'getItem' | 'setItem'>
}

export interface UpdaterState {
  phase: UpdatePhase
  currentVersion: string
  latest: { version: string; date?: string; body?: string } | null
  error: string
  progress: {
    received: number
    total: number
    percent: number
    bytesPerSecond: number
    elapsedMs: number
  }
  lastCheckedAt: number | null
  autoCheck: boolean
  backup: UpdateBackup | null
}

const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000
const LAST_CHECK_KEY = 'yijing.update.lastCheck'
const AUTO_KEY = 'yijing.update.auto'

const defaultStorage = (): Pick<Storage, 'getItem' | 'setItem'> | null => {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage
  } catch {
    return null
  }
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '—'
  const units = ['B', 'KiB', 'MiB', 'GiB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  const digits = value >= 100 || unit === 0 ? 0 : 1
  return `${value.toFixed(digits)} ${units[unit]}`
}

export function formatSpeed(bytesPerSecond: number): string {
  if (!Number.isFinite(bytesPerSecond) || bytesPerSecond <= 0) return '—'
  return `${formatBytes(bytesPerSecond)}/s`
}

export function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return '—'
  const totalSeconds = Math.round(ms / 1000)
  if (totalSeconds < 60) return `${totalSeconds} 秒`
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes} 分 ${String(seconds).padStart(2, '0')} 秒`
}

/** 把插件抛出的错误归类成「离线 / 其他错误」，用于给出可执行的提示。 */
export function classifyUpdateError(error: unknown, online: boolean): { offline: boolean; message: string } {
  const message = error instanceof Error ? error.message : String(error ?? '')
  if (!online) return { offline: true, message: '当前处于离线状态，无法检查更新。' }
  const offlinePattern = /(network|fetch|econn|dns|connect|timeout|timed out|délai|dns|unreachable|502|503|504)/i
  if (offlinePattern.test(message)) {
    return { offline: true, message: '无法连接更新服务（网络不可达或超时）。本地起卦、阅读与历史记录不受影响。' }
  }
  return { offline: false, message: message || '更新过程失败，请稍后重试。' }
}

export function createUpdater(deps: UpdaterDeps) {
  const now = deps.now ?? (() => Date.now())
  const storage = deps.storage ?? defaultStorage()

  const readNumber = (key: string): number | null => {
    const raw = storage?.getItem(key)
    if (!raw) return null
    const value = Number(raw)
    return Number.isFinite(value) ? value : null
  }
  const readBool = (key: string, fallback: boolean): boolean => {
    const raw = storage?.getItem(key)
    if (raw === null || raw === undefined) return fallback
    return raw === 'true'
  }
  const write = (key: string, value: string) => {
    try {
      storage?.setItem(key, value)
    } catch {
      /* 无痕模式或存储被禁用：仅本次会话生效 */
    }
  }

  const state = reactive<UpdaterState>({
    phase: deps.isDesktop() ? 'idle' : 'unsupported',
    currentVersion: '',
    latest: null,
    error: '',
    progress: { received: 0, total: 0, percent: 0, bytesPerSecond: 0, elapsedMs: 0 },
    lastCheckedAt: readNumber(LAST_CHECK_KEY),
    autoCheck: readBool(AUTO_KEY, true),
    backup: null,
  })

  let pending: RemoteUpdate | null = null
  let busy = false

  const isBusy = computed(() => busy)

  function resetProgress() {
    state.progress = { received: 0, total: 0, percent: 0, bytesPerSecond: 0, elapsedMs: 0 }
  }

  function releasePending() {
    const update = pending
    pending = null
    void update?.close?.().catch(() => {})
  }

  async function loadCurrentVersion() {
    if (!deps.isDesktop()) return
    try {
      state.currentVersion = await deps.getVersion()
    } catch {
      state.currentVersion = ''
    }
  }

  function isDue(): boolean {
    if (!state.autoCheck) return false
    if (state.lastCheckedAt === null) return true
    return now() - state.lastCheckedAt >= CHECK_INTERVAL_MS
  }

  /** 手动或自动检查。manual=false 时失败不打扰用户（静默降级），只记录状态。 */
  async function check(options: { manual?: boolean } = {}): Promise<void> {
    const manual = options.manual ?? true
    if (!deps.isDesktop()) {
      state.phase = 'unsupported'
      return
    }
    if (busy) return
    busy = true
    state.error = ''
    state.phase = 'checking'
    try {
      const update = await deps.checkUpdate()
      write(LAST_CHECK_KEY, String(now()))
      state.lastCheckedAt = now()
      if (!update) {
        releasePending()
        state.latest = null
        state.phase = 'up_to_date'
        return
      }
      releasePending()
      pending = update
      state.latest = { version: update.version, date: update.date, body: update.body }
      state.phase = 'available'
    } catch (error) {
      const { offline, message } = classifyUpdateError(error, typeof navigator === 'undefined' ? true : navigator.onLine)
      state.phase = offline ? 'offline' : 'error'
      state.error = message
      if (!manual) {
        // 自动检查失败：保持安静，下次到点再试，不阻塞任何本地功能
        state.phase = offline ? 'offline' : 'error'
      }
    } finally {
      busy = false
    }
  }

  /** 用户点「稍后」：保留可更新的信息，但不下载。 */
  function defer() {
    if (state.phase !== 'available') return
    state.phase = 'deferred'
  }

  /** 关闭错误/离线提示，回到 idle。 */
  function dismiss() {
    if (state.phase === 'deferred') return
    if (busy) return
    state.phase = state.latest ? 'deferred' : 'idle'
    state.error = ''
  }

  /**
   * 下载 → 备份 → 停 sidecar → 安装 → 重启。
   * 任何一步失败都保留已下载状态并给出可重试的错误；备份失败时不进入安装。
   */
  async function downloadAndInstall(): Promise<void> {
    if (!deps.isDesktop() || busy) return
    const update = pending
    if (!update) {
      state.phase = 'error'
      state.error = '没有可安装的更新，请先重新检查。'
      return
    }
    busy = true
    state.error = ''
    state.backup = null
    resetProgress()
    state.phase = 'downloading'
    const startedAt = now()
    try {
      await update.download((event) => {
        if (event.event === 'Started') {
          state.progress.total = event.data?.contentLength ?? 0
        } else if (event.event === 'Progress') {
          state.progress.received += event.data?.chunkLength ?? 0
          const elapsed = Math.max(now() - startedAt, 1)
          state.progress.elapsedMs = elapsed
          state.progress.bytesPerSecond = (state.progress.received / elapsed) * 1000
          state.progress.percent = state.progress.total > 0
            ? Math.min(100, Math.round((state.progress.received / state.progress.total) * 1000) / 10)
            : 0
        } else if (event.event === 'Finished') {
          state.progress.percent = 100
        }
      })

      state.phase = 'installing'
      try {
        state.backup = await deps.backupDatabase()
      } catch (error) {
        // 备份失败 = 不安装；此时 sidecar 仍在运行，业务无中断
        const { message } = classifyUpdateError(error, true)
        state.phase = 'error'
        state.error = `安装前备份失败，已取消安装：${message}`
        releasePending()
        return
      }

      const preparation = await deps.prepareForUpdate()
      if (!preparation.stopped) {
        state.phase = 'error'
        state.error = '本地服务未能停止，已取消安装。请关闭其它窗口后重试。'
        releasePending()
        return
      }

      await update.install()
      state.phase = 'completed'
      releasePending()
      await deps.relaunch()
    } catch (error) {
      const { offline, message } = classifyUpdateError(error, typeof navigator === 'undefined' ? true : navigator.onLine)
      state.phase = offline ? 'offline' : 'error'
      state.error = message
    } finally {
      busy = false
    }
  }

  function setAutoCheck(value: boolean) {
    state.autoCheck = value
    write(AUTO_KEY, String(value))
  }

  /** 启动时调用：只在桌面端、开启自动检查且距上次检查超过 24 小时时触发。 */
  async function init(): Promise<void> {
    await loadCurrentVersion()
    if (!deps.isDesktop()) return
    if (!isDue()) return
    await check({ manual: false })
  }

  return {
    state: readonly(state),
    isBusy,
    isDue,
    init,
    check,
    defer,
    dismiss,
    downloadAndInstall,
    setAutoCheck,
  }
}

export type Updater = ReturnType<typeof createUpdater>

/** 真实环境绑定：动态 import，浏览器里永远不会触达 Tauri 原生接口。 */
let singleton: Updater | null = null

export function useUpdater(): Updater {
  if (singleton) return singleton
  const desktop = import.meta.env.MODE !== 'test' && isDesktopRuntime()
  singleton = createUpdater({
    isDesktop: () => desktop,
    getVersion: async () => {
      const { getVersion } = await import('@tauri-apps/api/app')
      return getVersion()
    },
    checkUpdate: async () => {
      const { check } = await import('@tauri-apps/plugin-updater')
      const update = await check({ timeout: 20000 })
      return update ? (update as unknown as RemoteUpdate) : null
    },
    relaunch: async () => {
      const { relaunch } = await import('@tauri-apps/plugin-process')
      await relaunch()
    },
    prepareForUpdate: async () => {
      const { invoke } = await import('@tauri-apps/api/core')
      return invoke<UpdatePreparation>('prepare_for_update')
    },
    backupDatabase: async () => {
      const { api } = await import('./api')
      return api.updateBackup()
    },
  })
  return singleton
}

function isDesktopRuntime(): boolean {
  if (typeof window === 'undefined') return false
  const internals = (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__
  return Boolean(internals)
}
