import { invoke, isTauri } from '@tauri-apps/api/core'

/** Desktop path selection and writing stay together in the native command. */
export async function saveMarkdown(filename: string, markdown: string): Promise<boolean> {
  if (isTauri()) return invoke<boolean>('export_markdown', { filename, markdown })
  const url = URL.createObjectURL(new Blob([markdown], { type: 'text/markdown;charset=utf-8' }))
  const anchor = document.createElement('a')
  try {
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
  } finally {
    anchor.remove()
    // Leave the URL alive until the browser has started consuming the download.
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }
  return true
}
