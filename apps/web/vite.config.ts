import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',  // 相对路径，适配 proxy
  server: {
    proxy: {
      // dev 模式：前端在 5173，后端在 8000，API 经代理转发
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // make dev 下 Vite 比 API 先就绪（API 启动要过 PG 校验等 lifespan 流程），
        // 旧标签页的 SSE 自动重连会撞上未监听窗口，喷 ECONNREFUSED 全栈报错。
        // 这里改成：一行友好提示（限频）+ 直接断开该次代理，让前端的重连逻辑自己重试。
        configure: (proxy) => {
          let lastNotice = 0
          proxy.on('error', (err, _req, res) => {
            const now = Date.now()
            if (now - lastNotice > 5000) {
              lastNotice = now
              console.log('[vite] API 未就绪或中断，浏览器会自动重连（5 秒内合并提示）')
            }
            const r = res as import('node:http').ServerResponse | import('node:net').Socket
            if ('writeHead' in r && !r.headersSent) {
              r.writeHead(502, { 'Content-Type': 'text/plain' })
              r.end('API not ready')
            }
            void err
          })
        },
      },
    },
  },
})
