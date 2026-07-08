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
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
