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
        // The default is a fallback, NOT the truth: the published backend port is per-repo-
        // instance (parallel checkouts each publish their own), so it lives in infra/.env's
        // BACKEND_PORT and reaches this file through VITE_API_PROXY_TARGET. Set that env var.
        //
        // This comment used to claim "8100 matches infra/.env's BACKEND_PORT". It did not —
        // infra/.env says 8001 — so the line asserting the two agreed was itself the drift it
        // warned about. The default is left at 8100 rather than re-pinned to today's 8001:
        // pinning it would just re-stage the same false claim for the next reader, and the
        // number here cannot be right for every checkout anyway.
        //
        // What is NOT arbitrary is that the default avoids 8000: another service occupies 8000
        // on this host, so a dev who forgot the env var would not get a connection error — they
        // would get someone else's app answering, which is the failure that costs an afternoon.
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
