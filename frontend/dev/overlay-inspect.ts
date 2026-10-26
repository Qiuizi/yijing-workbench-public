/**
 * 开发期自检入口：把 Element Plus 的浮层与表单状态集中渲染出来，
 * 供深浅两套主题截图与自动化断言。
 *
 * 不是产品页面：只在 `vite dev` 下可访问（生产构建只打包 index.html）。
 * 访问：http://127.0.0.1:5194/dev/overlay-inspect.html?theme=dark
 */
import { createApp } from 'vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import '../src/theme.css'
import '../src/dark.css'
import Harness from './overlay-harness.vue'

const theme = new URLSearchParams(location.search).get('theme') === 'dark' ? 'dark' : 'light'
document.documentElement.dataset.theme = theme
document.documentElement.classList.toggle('dark', theme === 'dark')
document.documentElement.style.colorScheme = theme
document.body.style.margin = '0'
document.body.style.background = 'var(--bg)'
document.body.style.color = 'var(--text-primary)'
document.body.style.fontFamily = 'var(--font-ui)'

createApp(Harness).mount('#app')

Object.assign(window, { __theme: theme })
