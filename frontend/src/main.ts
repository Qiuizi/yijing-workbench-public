import { createApp } from 'vue'
import {
  ElButton,
  ElCheckbox,
  ElDrawer,
  ElForm,
  ElIcon,
  ElInput,
  ElLoading,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
} from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './theme.css'
import './style.css'
import './redesign.css'
import './dark.css'
import App from './App.vue'
import { initAppearance } from './appearance'

// 主题必须在挂载前定好，避免首屏闪白或闪黑。
initAppearance()

const app = createApp(App)

for (const component of [
  ElButton,
  ElCheckbox,
  ElDrawer,
  ElForm,
  ElIcon,
  ElInput,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
]) {
  app.component(component.name!, component)
}

app.directive('loading', ElLoading.directive)
app.mount('#app')
