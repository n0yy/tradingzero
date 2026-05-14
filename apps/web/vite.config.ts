import path from 'node:path'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const skipHtmlNavigation = (req: { headers: Record<string, string | string[] | undefined> }) => {
  const accept = req.headers.accept
  const acceptStr = Array.isArray(accept) ? accept.join(',') : accept ?? ''
  if (acceptStr.includes('text/html')) return req.headers.referer ? null : '/index.html'
  return null
}

const apiOrigin = process.env.TRADINGZERO_API_ORIGIN ?? 'http://127.0.0.1:8000'
const wsOrigin = apiOrigin.replace(/^http/i, 'ws')

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 4173,
    proxy: {
      '/runs': { target: apiOrigin, changeOrigin: true, bypass: skipHtmlNavigation },
      '/config': { target: apiOrigin, changeOrigin: true, bypass: skipHtmlNavigation },
      '/healthz': { target: apiOrigin, changeOrigin: true },
      '/ws': { target: wsOrigin, ws: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test-setup.ts',
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
  },
})
