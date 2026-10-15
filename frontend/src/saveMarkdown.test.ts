import { afterEach, describe, expect, it, vi } from 'vitest'
import { invoke, isTauri } from '@tauri-apps/api/core'
import { saveMarkdown } from './saveMarkdown'

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn(), isTauri: vi.fn() }))
afterEach(() => { vi.resetAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers() })

describe('Markdown save transport', () => {
  it('uses one native command for selection and writing, and silently returns cancellation', async () => {
    vi.mocked(isTauri).mockReturnValue(true)
    vi.mocked(invoke).mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    expect(await saveMarkdown('中文.md', '# 中文')).toBe(false)
    expect(invoke).toHaveBeenCalledWith('export_markdown', { filename: '中文.md', markdown: '# 中文' })
    expect(await saveMarkdown('中文.md', '# 中文')).toBe(true)
  })

  it('propagates the native write error for the UI to display', async () => {
    vi.mocked(isTauri).mockReturnValue(true)
    vi.mocked(invoke).mockRejectedValue(new Error('无法保存 Markdown 文件：拒绝访问'))
    await expect(saveMarkdown('中文.md', '# 中文')).rejects.toThrow('拒绝访问')
  })

  it('downloads a UTF-8 Markdown Blob in the browser and cleans up resources', async () => {
    vi.useFakeTimers()
    vi.mocked(isTauri).mockReturnValue(false)
    const anchor = { href: '', download: '', click: vi.fn(), remove: vi.fn() }
    const createObjectURL = vi.fn().mockReturnValue('blob:test')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
    vi.stubGlobal('document', { createElement: vi.fn().mockReturnValue(anchor), body: { appendChild: vi.fn() } })
    expect(await saveMarkdown('合成.md', '# 中文\n\n卦象')).toBe(true)
    const blob = createObjectURL.mock.calls[0]![0] as Blob
    expect(blob.type).toBe('text/markdown;charset=utf-8')
    expect(await blob.text()).toBe('# 中文\n\n卦象')
    expect(anchor.download).toBe('合成.md')
    expect(anchor.click).toHaveBeenCalledOnce()
    expect(anchor.remove).toHaveBeenCalledOnce()
    vi.runAllTimers()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test')
    expect(invoke).not.toHaveBeenCalled()
  })
})
