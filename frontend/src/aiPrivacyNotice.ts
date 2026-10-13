import { h } from 'vue'
import { ElMessageBox } from 'element-plus'

export const DEEPSEEK_PRIVACY_URL = 'https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html?locale=en_US'
export const DEEPSEEK_PLATFORM_TERMS_URL = 'https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html'
export const MICROSOFT_PRIVACY_URL = 'https://privacy.microsoft.com/privacystatement'
export const WEBVIEW2_PRIVACY_URL = 'https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/data-privacy'

const ACKNOWLEDGEMENT_KEY = 'yijing.ai-network-privacy.v1'

function wasAcknowledged(): boolean {
  try {
    return globalThis.localStorage?.getItem(ACKNOWLEDGEMENT_KEY) === 'accepted'
  } catch {
    return false
  }
}

export function markAIPrivacyAcknowledged(): void {
  try {
    globalThis.localStorage?.setItem(ACKNOWLEDGEMENT_KEY, 'accepted')
  } catch {
    // Per-send confirmations remain active if this WebView cannot persist the acknowledgement.
  }
}

export async function requireAIPrivacyAcknowledgement(): Promise<boolean> {
  if (wasAcknowledged()) return true

  const content = h('div', { class: 'ai-consent-detail' }, [
    h('p', '此操作会通过 HTTPS 连接 DeepSeek API。读取模型清单、验证连接或校验模型时，应用会将 API Key 作为 Bearer 身份验证信息发送；这些操作不发送起卦问题或聊天内容。每次 AI 对话请求也会携带该密钥进行身份验证。'),
    h('p', 'AI 请求还会发送本条消息、当前起卦问题与卦象上下文，以及当前 AI 会话此前消息。AI 结果保存在本机 SQLite。DeepSeek 对请求数据的处理和留存依其适用的开放平台条款；本应用不承诺服务方不会保存数据。'),
    h('p', '拒绝后不会连接 DeepSeek；铜钱起卦、手动起卦、排盘和本地历史仍可使用。'),
    h('p', [
      'DeepSeek 隐私政策：',
      h('a', { href: DEEPSEEK_PRIVACY_URL, target: '_blank', rel: 'noopener noreferrer' }, '查看政策'),
      '；开放平台条款：',
      h('a', { href: DEEPSEEK_PLATFORM_TERMS_URL, target: '_blank', rel: 'noopener noreferrer' }, '查看条款'),
    ]),
  ])

  try {
    await ElMessageBox.confirm(content, '连接 DeepSeek 前请阅读', {
      confirmButtonText: '知悉并继续',
      cancelButtonText: '取消并保持本地',
      type: 'warning',
      distinguishCancelAndClose: true,
      dangerouslyUseHTMLString: false,
    })
  } catch {
    return false
  }

  markAIPrivacyAcknowledged()
  return true
}
