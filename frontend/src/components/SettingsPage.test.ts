import { createSSRApp, defineComponent, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import SettingsPage from './SettingsPage.vue'
import { readFileSync } from 'node:fs'
import { version as appVersion, bundle } from '../../src-tauri/tauri.conf.json'
import { version as frontendVersion } from '../../package.json'
import packageLock from '../../package-lock.json'

async function renderSettings() {
  const app = createSSRApp(SettingsPage)
  app.component('el-input', defineComponent({ setup: (_, { attrs }) => () => h('input', attrs) }))
  app.component('el-select', defineComponent({ setup: (_, { attrs, slots }) => () => h('div', attrs, slots.default?.()) }))
  app.component('el-option', defineComponent({ setup: (_, { attrs }) => () => h('span', attrs) }))
  app.component('el-button', defineComponent({ setup: (_, { attrs, slots }) => () => h('button', attrs, slots.default?.()) }))
  app.directive('loading', () => {})
  return renderToString(app)
}

describe('SettingsPage grouping', () => {
  it('shows the persistent local and external data notices without rendering a secret value', async () => {
    const html = await renderSettings()
    expect(html).toContain('起卦')
    expect(html).toContain('历法')
    expect(html).toContain('AI 辅助')
    expect(html).toContain('本地与联网隐私说明')
    expect(html).toContain('WebView2 SmartScreen')
    expect(html).toContain('关闭 AI 后')
    expect(html).toContain('https://privacy.microsoft.com/privacystatement')
    expect(html).toContain(`V${appVersion}`)
    expect(html).toContain('关于')
    expect(html).toContain('当前界面版本')
    expect(html).toContain('应用代码许可证')
    expect(html).toContain('未配置')
    expect(html).not.toContain('show-password')
    expect(html).not.toContain('API Key 明文')
  })

  it('uses the application version and shows the repository LICENSE with separate license scopes', async () => {
    const html = await renderSettings()
    expect(appVersion).toBe(frontendVersion)
    expect(packageLock.version).toBe(appVersion)
    expect(packageLock.packages[''].version).toBe(appVersion)
    const cargo = readFileSync(new URL('../../src-tauri/Cargo.toml', import.meta.url), 'utf8')
    const cargoLock = readFileSync(new URL('../../src-tauri/Cargo.lock', import.meta.url), 'utf8')
    expect(cargo.match(/^version = "([^"]+)"/m)?.[1]).toBe(appVersion)
    for (const newline of ['\n', '\r\n']) {
      const platformLock = cargoLock.replace(/\r?\n/g, newline)
      expect(platformLock.match(/name = "yijing-workbench"\r?\nversion = "([^"]+)"/)?.[1]).toBe(appVersion)
    }
    expect(html).toContain(`V${appVersion}`)
    expect(html).toContain('V3.1.4')
    expect(html).toContain('MIT，仅适用于 Qiuizi 有权授权的项目自有代码')
    expect(html).toContain('原创 SVG 与生成图标')
    expect(html).toContain('适用独立来源许可，来源页面标注 CC BY-SA 4.0')
    expect(html).toContain('不覆盖古籍数据或第三方组件')
    expect(html).toContain('各自适用独立许可证，详见随附 THIRD_PARTY_NOTICES.txt')
    expect(html).not.toContain('未发现 LICENSE')

    // Read independently of Vite and the process working directory. The same
    // source is embedded in the frontend and bundled as LICENSE by Tauri.
    expect(bundle.resources['../../LICENSE']).toBe('LICENSE')
    const license = readFileSync(new URL('../../../LICENSE', import.meta.url), 'utf8')
    const expectedLicense = await renderToString(createSSRApp({
      render: () => h('pre', { class: 'settings-license-text' }, license),
    }))
    expect(html).toContain('<summary>查看项目 LICENSE 全文</summary>')
    expect(html).toContain(expectedLicense)
  })
})
