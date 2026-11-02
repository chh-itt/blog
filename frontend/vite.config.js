import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // 开发环境代理：前端请求 /api 转发到 Django 后端 8100 端口
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8100',
        changeOrigin: true,
      },
      // 媒体文件（头像等）同样代理到后端
      '/media': {
        target: 'http://127.0.0.1:8100',
        changeOrigin: true,
      },
    },
  },
})
