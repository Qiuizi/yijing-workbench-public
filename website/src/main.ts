import { createApp } from 'vue'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.vue'

const locale: 'zh' | 'en' = document.documentElement.dataset.locale === 'en' ? 'en' : 'zh'

createApp(App, { locale }).mount('#app')
