import { createSSRApp, defineComponent, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import SettingsPage from './SettingsPage.vue'

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
    expect(html).toContain('V3.2.2')
    expect(html).toContain('关于')
    expect(html).toContain('当前界面版本')
    expect(html).toContain('应用代码许可证')
    expect(html).toContain('未配置')
    expect(html).not.toContain('show-password')
    expect(html).not.toContain('API Key 明文')
  })
})
