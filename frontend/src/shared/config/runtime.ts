// Values that differ between a laptop, the dev stand and production.
//
// The jury's remark named `POLL_INTERVAL_MS = 5000` — a number that decides how hard the client
// hammers the API, compiled into a hook where no deployment can reach it. The stand and a local
// backend do not want the same cadence, and finding that out meant a rebuild.
//
// Everything here reads `import.meta.env` once, with a default that is the value the product was
// built and tested against, and a floor so a mistyped variable cannot turn the client into a
// flood. `VITE_` prefixed names are the only ones Vite exposes to the browser.

function positiveInt(raw: string | undefined, fallback: number, floor: number): number {
  const parsed = Number(raw)
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback
  return Math.max(floor, Math.trunc(parsed))
}

export const RUNTIME = {
  // How often a running generation is asked for its status, and for how long. The product of the
  // two is the ceiling on a single generation: 5s × 60 ≈ 5 minutes.
  generationPollIntervalMs: positiveInt(import.meta.env.VITE_GENERATION_POLL_INTERVAL_MS, 5000, 1000),
  generationPollMaxAttempts: positiveInt(import.meta.env.VITE_GENERATION_POLL_MAX_ATTEMPTS, 60, 1),

  // Consecutive failed status checks tolerated before a run is called lost. Not zero: over five
  // minutes of polling one transient 502 is likely rather than exceptional, and treating it as
  // fatal tells the user their generation failed while the server is still writing it.
  generationPollMaxConsecutiveFailures: positiveInt(
    import.meta.env.VITE_GENERATION_POLL_MAX_FAILURES,
    3,
    1,
  ),
} as const
