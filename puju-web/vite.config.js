import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发模式：vite dev(5173) 通过代理转发 /api 到 FastAPI(8000)，无跨域问题
// 生产模式：npm run build 产出 dist/，由 FastAPI 直接托管（见 app/api/main.py）
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
