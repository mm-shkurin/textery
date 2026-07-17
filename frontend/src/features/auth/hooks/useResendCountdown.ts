import { useEffect, useMemo, useState } from 'react'

// The wait between resend attempts, in seconds. A client-side courtesy only: it stops the
// impatient double-click, it does not enforce anything. The rate limit that matters is the
// server's, and this countdown does not know what it is.
export const RESEND_COUNTDOWN_SECONDS = 60

const SECOND_MS = 1000

export interface ResendCountdown {
  // Seconds left; 0 means a resend is allowed.
  secondsLeft: number
  // 'MM:SS', for display.
  formatted: string
  isElapsed: boolean
  restart: () => void
}

function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

// A countdown that actually counts.
//
// VerifyCodeForm previously held `const [countdownSeconds] = useState(60)` — no setter, no timer.
// It rendered a frozen `01:00` for as long as the screen was open, and the resend button ignored
// it entirely: a rate-limit hint that neither counted nor limited. Extracted to a hook so the
// ticking is testable on its own, and so the form is not the place that owns a clock.
//
// Derived from a DEADLINE rather than decremented per tick. A `setSeconds(s => s - 1)` chain
// makes the displayed number a running total of how often the timer fired, which is not the same
// as elapsed time: every tick carries scheduling lag, and a backgrounded tab has its timers
// throttled to once a minute or so — so the chain silently under-counts and the button unlocks
// late, or never while the tab is hidden. Reading the clock each tick means a missed or late
// firing costs display latency, never correctness: the next render tells the truth regardless of
// how many ticks were dropped.
export function useResendCountdown(initialSeconds = RESEND_COUNTDOWN_SECONDS): ResendCountdown {
  const [deadline, setDeadline] = useState(() => Date.now() + initialSeconds * SECOND_MS)
  const [now, setNow] = useState(() => Date.now())

  const secondsLeft = useMemo(
    () => Math.max(0, Math.ceil((deadline - now) / SECOND_MS)),
    [deadline, now],
  )

  useEffect(() => {
    if (secondsLeft <= 0) return
    const timer = setInterval(() => setNow(Date.now()), SECOND_MS)
    return () => clearInterval(timer)
  }, [secondsLeft])

  return useMemo(
    () => ({
      secondsLeft,
      formatted: formatCountdown(secondsLeft),
      isElapsed: secondsLeft <= 0,
      restart: () => {
        const next = Date.now()
        setNow(next)
        setDeadline(next + initialSeconds * SECOND_MS)
      },
    }),
    [secondsLeft, initialSeconds],
  )
}
