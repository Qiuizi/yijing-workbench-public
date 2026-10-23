import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// base is fixed to the GitHub Pages project path.
export default defineConfig({
  base: '/yijing-workbench-public/',
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: {
        main: 'index.html',
        en: 'en/index.html',
      },
    },
  },
})
