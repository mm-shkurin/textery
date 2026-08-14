import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const frontendPort = Number(process.env.FRONTEND_PORT) || 5173

// Is this run going to serve the app to a browser, i.e. does the proxy matter?
//
// `command` is 'serve' for `vite dev` AND for `vitest`, which loads this same config; the tests
// never reach the proxy, so demanding the variable there would fail the suite over a value it
// does not use. `VITEST` is set by the runner itself.
function servesBrowser(command: string): boolean {
  return command === 'serve' && !process.env.VITEST
}

// The dev proxy needs a real backend address, and only the checkout knows it.
function requireProxyTarget(): string {
  const target = process.env.VITE_API_PROXY_TARGET
  if (target) return target
  throw new Error(
    'VITE_API_PROXY_TARGET is not set. The dev server proxies /api to the backend, and the ' +
      'port is per-checkout. Copy .env.example to .env and set it from infra/.env:\n' +
      '  grep BACKEND_PORT ../infra/.env',
  )
}

// https://vite.dev/config/
// Function form so the proxy target is demanded only when a dev server is actually started:
// `vitest` loads this same file, and a throw at module scope would fail the test run over a
// variable the tests never use.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api': {
        // No fallback on purpose. The published backend port is per-checkout — it lives in
        // infra/.env's BACKEND_PORT and reaches here through VITE_API_PROXY_TARGET. A default
        // would be wrong for everyone but its author, and wrong quietly: the dev server would
        // start, the app would load, and every request would go to whatever else holds that
        // port on this host. Missing config fails here, once, with the fix in the message.
        target: servesBrowser(command) ? requireProxyTarget() : '',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    // Pinned so the suite's dates do not depend on the runner's zone. This checkout resolves
    // Asia/Omsk and passes; a US-zone CI runner renders the epoch fixture as '31 декабря 1969'
    // and fails — verified, and it was the ONLY zone-dependent test in the suite.
    //
    // Moscow rather than UTC, deliberately. UTC would fix the epoch fixture too, but it makes
    // local-year and UTC-year identical by construction — and the queued
    // 'a 31 December evening does not read as next year' step needs exactly the case where they
    // DIFFER, which under UTC cannot be written at all. Moscow is DST-free (Russia, since 2014),
    // so the offset is a constant rather than a function of the date, and it is production-like
    // for a Russian-language product.
    //
    // Set via `env` (in-process) and not a `TZ=` shell prefix: on Windows a shell TZ var is
    // ignored by Node — it still resolved Asia/Omsk — so a `TZ=UTC vitest` script would be a
    // silent no-op and the pin would be a lie.
    env: { TZ: 'Europe/Moscow' },
    // Strictly above setup.ts's `asyncUtilTimeout: 5000`, and that gap is the whole point. The two
    // were equal (5000 is vitest's default here), so on every red where an element never arrives the
    // two deadlines tied and the OUTER one won: vitest killed the test before Testing Library could
    // raise its own «Unable to find role/testid» error with the rendered-DOM dump. The recorded
    // evidence was `Test timed out in 5000ms` — identical output whether the element is genuinely
    // missing, `vi.mock` failed to apply, or the component rendered nothing at all. Story 12's
    // scenario 1.1 recorded three prediction matches against that string before this was raised.
    //
    // Raised here rather than lowering asyncUtilTimeout: that 5000 is a measured chunk-load budget
    // (see setup.ts), so cutting it would trade unreadable failures for flaky ones.
    testTimeout: 10000,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      // json-summary feeds scripts/check-per-file-coverage.mjs, which enforces the floor the
      // global thresholds below cannot: a single untested module hides inside a good aggregate.
      reporter: ['text', 'html', 'json-summary'],
      // Config, CSS and the test harness itself are not subjects — counting them would move the
      // ratio without telling anyone anything.
      exclude: ['src/main.tsx', 'src/test/**', '**/*.d.ts', '**/__tests__/**'],
      // A FLOOR set just under today's measured numbers, not an aspiration. Its job is to fail
      // the run when coverage DROPS — which is how historyApi.ts sat at 0% while every caller
      // mocked it and the suite stayed green. Raise these as coverage rises; never lower them to
      // make a run pass.
      // Ratcheted to sit ~1 pt under the measured 97.25 / 93.01 / 99.02 / 98.43. One point is
      // deliberate on both sides: tighter and an unrelated refactor turns the build red for
      // rounding, looser and a real regression slips through — which is exactly how historyApi.ts
      // sat at 0% while every caller mocked it and the suite stayed green. Raise as coverage
      // rises; never lower to make a red run pass.
      //
      // The measured numbers dipped once and the floors did NOT follow: story 12's «Мои проекты»
      // landed with almost no tests and dropped the aggregate to 92.37 / 86 / 94.16 / 94.55, which
      // is what these four turned red on. They stayed where they were and the feature got its
      // tests; that is the direction this gate is only useful in.
      thresholds: {
        statements: 96,
        branches: 92,
        functions: 98,
        lines: 97,
      },
    },
  },
}))
