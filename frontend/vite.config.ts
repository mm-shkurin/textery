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
        // A fallback, not the truth: the published backend port is per-checkout, lives in
        // infra/.env's BACKEND_PORT, and reaches here via VITE_API_PROXY_TARGET. Set that.
        // The one constraint on the fallback is that it must not be 8000 — another service
        // occupies that port on this host, so forgetting the env var would not fail loudly, it
        // would silently proxy to someone else's app.
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
