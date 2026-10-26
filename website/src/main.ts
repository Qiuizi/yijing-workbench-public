import { createApp } from 'vue'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.vue'
import { ensureThemeApplied } from './theme'

const locale: 'zh' | 'en' = document.documentElement.dataset.locale === 'en' ? 'en' : 'zh'

// 内联脚本已在首屏前定好主题；这里兜底处理脚本被拦截或语言页复用的情形。
ensureThemeApplied()

createApp(App, { locale }).mount('#app')
