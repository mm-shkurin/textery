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
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      // Config, CSS and the test harness itself are not subjects — counting them would move the
      // ratio without telling anyone anything.
      exclude: ['src/main.tsx', 'src/test/**', '**/*.d.ts', '**/__tests__/**'],
      // A FLOOR set just under today's measured numbers, not an aspiration. Its job is to fail
      // the run when coverage DROPS — which is how historyApi.ts sat at 0% while every caller
      // mocked it and the suite stayed green. Raise these as coverage rises; never lower them to
      // make a run pass.
      // Ratcheted to sit ~1 pt under the measured 96.06 / 89.90 / 99.69 / 97.92. One point is
      // deliberate on both sides: tighter and an unrelated refactor turns the build red for
      // rounding, looser and a real regression slips through — which is exactly how historyApi.ts
      // sat at 0% while every caller mocked it and the suite stayed green. Raise as coverage
      // rises; never lower to make a red run pass.
      thresholds: {
        statements: 95,
        branches: 89,
        functions: 98,
        lines: 97,
      },
    },
  },
})
