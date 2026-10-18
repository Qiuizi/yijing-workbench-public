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
import './style.css'
import './redesign.css'
import App from './App.vue'

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
