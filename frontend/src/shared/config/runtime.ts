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

// Same, for a value that is a ratio rather than a count: `Math.trunc` would turn a 1.5x backoff
// factor into 1 and quietly disable the backoff entirely, so this one keeps the fraction.
function positiveRatio(raw: string | undefined, fallback: number, floor: number): number {
  const parsed = Number(raw)
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback
  return Math.max(floor, parsed)
}

function csv(raw: string | undefined, fallback: string[]): readonly string[] {
  const parts = (raw ?? '')
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean)
  return parts.length > 0 ? parts : fallback
}

export const RUNTIME = {
  // How often a running generation is asked for its status, and for how long. The product of the
  // two is the ceiling on a single generation: 5s × 60 ≈ 5 minutes.
  generationPollIntervalMs: positiveInt(
    import.meta.env.VITE_GENERATION_POLL_INTERVAL_MS,
    5000,
    1000,
  ),
  generationPollMaxAttempts: positiveInt(import.meta.env.VITE_GENERATION_POLL_MAX_ATTEMPTS, 60, 1),

  // The poll is not a fixed cadence: each check that finds nothing new waits longer than the last.
  // A generation takes minutes, so the first seconds are the only ones where a 5s question is
  // likely to be answered by news; after that a fixed 5s is the client asking sixty times to be
  // told the same thing sixty times. The delay is multiplied by the factor per unwitnessed tick
  // and clamped at the ceiling, and it drops back to the base interval the moment the run's status
  // actually changes — the phase right after a transition is when the next one is most likely.
  //
  // 1.5 rather than the usual doubling: the ceiling has to be reached in a handful of steps
  // without the very first gap after a change being long enough to be felt as lag (5 → 7.5 → 11.2
  // → 16.9 → 25.3 → 30). 30s is the ceiling because it is the longest a user watching a progress
  // screen will accept between updates, and it is still comfortably inside the request timeout.
  generationPollBackoffFactor: positiveRatio(
    import.meta.env.VITE_GENERATION_POLL_BACKOFF_FACTOR,
    1.5,
    1,
  ),
  generationPollMaxIntervalMs: positiveInt(
    import.meta.env.VITE_GENERATION_POLL_MAX_INTERVAL_MS,
    30000,
    1000,
  ),

  // Consecutive failed status checks tolerated before a run is called lost. Not zero: over five
  // minutes of polling one transient 502 is likely rather than exceptional, and treating it as
  // fatal tells the user their generation failed while the server is still writing it.
  generationPollMaxConsecutiveFailures: positiveInt(
    import.meta.env.VITE_GENERATION_POLL_MAX_FAILURES,
    3,
    1,
  ),

  // Autosave backoff. The editor retries a failed save on a doubling delay from base to max; a
  // stand with a slower backend wants a longer floor, and that is a deployment's call.
  autosaveRetryBaseMs: positiveInt(import.meta.env.VITE_AUTOSAVE_RETRY_BASE_MS, 1000, 250),
  autosaveRetryMaxMs: positiveInt(import.meta.env.VITE_AUTOSAVE_RETRY_MAX_MS, 8000, 1000),

  // How long «Изменения сохранены» stays on screen after a profile write. Long enough to be read
  // by someone whose eyes were on the field they just edited (~3s of reading plus a beat), short
  // enough that it is gone before the next edit — a confirmation that outlives its cause reads as
  // a stuck UI rather than as feedback.
  profileSavedToastMs: positiveInt(import.meta.env.VITE_PROFILE_SAVED_TOAST_MS, 3200, 500),

  // Which image formats an avatar may be uploaded in. Policy, not logic: tightening or widening it
  // must not require a code change and a release.
  avatarTypes: csv(import.meta.env.VITE_AVATAR_TYPES, ['image/png', 'image/jpeg', 'image/webp']),

  // How long an analytics report may stay on the wire. Deliberately far below the product's own
  // 25s: that bound is sized for a document generation the user is waiting on, and nobody is
  // waiting on a telemetry POST. What the short bound buys is the browser's per-host connection
  // budget — a hung report holds one of the six, and the product's own calls queue behind it.
  analyticsTimeoutMs: positiveInt(import.meta.env.VITE_ANALYTICS_TIMEOUT_MS, 5000, 500),
} as const

// Not env-driven: these are facts, not deployment choices.

// One second, in milliseconds. Named so a countdown reads `deadline - now) / SECOND_MS` rather
// than repeating a bare 1000 that could be any duration.
export const SECOND_MS = 1000

// The window a rendered date must fall inside to be believed. A backend sentinel
// (`0001-01-01T00:00:00Z`, `9999-12-31T23:59:59Z` — what LocalDate.MIN, datetime.min and
// DateTime.MaxValue serialize to when a nullable column is mapped through a non-nullable field)
// arrives as a perfectly shaped, perfectly parseable ISO string: only its VALUE is wrong.
//
// Deliberately generous, and NOT derived from the current clock. `new Date().getFullYear()` as
// the ceiling would blank the date of a project the user edited seconds ago whenever their clock
// runs minutes behind the server's, and would do it to every project on every 31 December
// evening. The floor sits strictly below 1970 because `1970-01-01T00:00:00Z` is a genuinely
// renderable instant whose `getFullYear()` is 1969 in any negative-offset zone — a floor AT 1970
// would blank a real date.
export const EARLIEST_PLAUSIBLE_YEAR = 1900
export const LATEST_PLAUSIBLE_YEAR = 2200
