import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const frontendPort = Number(process.env.FRONTEND_PORT) || 5173

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api': {
        // 8100 matches infra/.env's BACKEND_PORT — the port the stack actually publishes
        // (`docker compose up backend` -> 0.0.0.0:8100->8000/tcp). The old 8000 default was not
        // merely stale: another service occupies 8000 on this host, so a dev who forgot the env
        // var did not get a connection error, they got someone else's app answering.
        target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8100',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
