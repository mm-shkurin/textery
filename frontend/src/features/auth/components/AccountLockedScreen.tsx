import { useEffect, useState } from 'react'
import { SECOND_MS } from '../../../shared/config/runtime'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import { formatMmSs } from '../utils/formatDuration'
import './AccountLockedScreen.css'

// The locked-screen copy lives HERE, in the form-side component — never in the loginApi mapper
// (round-8 premortem seam: the api reports the wire, the form owns display). The api sends
// message '' for ACCOUNT_LOCKED; these strings are the client's, same for every user.
const HEADING = 'Аккаунт временно заблокирован'
const SUBTITLE = 'Слишком много неудачных попыток входа. Попробуйте снова через некоторое время.'
const RETRY_PREFIX = 'Повторная попытка через '
const BACK_LABEL = 'Вернуться ко входу'

// Fallback window when the server sent no usable Retry-After (missing/non-numeric). Keeping the
// user locked for a sane default is safer than dropping the lock or rendering NaN — the exact
// remaining time is best-effort, the lock itself is not.
export const DEFAULT_LOCKOUT_SECONDS = 300

interface AccountLockedScreenProps {
  // Seconds until retry is allowed (from Retry-After). NaN/absent/non-positive falls back to the
  // default window above.
  retryAfterSeconds: number
  // Called when the lockout has elapsed OR the user asks to go back — both return to the login
  // form, so the parent clears the lockout state either way.
  onDismiss: () => void
}

export function AccountLockedScreen({ retryAfterSeconds, onDismiss }: AccountLockedScreenProps) {
  const initialSeconds =
    Number.isFinite(retryAfterSeconds) && retryAfterSeconds > 0
      ? Math.floor(retryAfterSeconds)
      : DEFAULT_LOCKOUT_SECONDS
  // The lock ends at a fixed INSTANT, computed once from the server's Retry-After. Everything
  // displayed is derived from that deadline rather than counted down step by step.
  const [deadline] = useState(() => Date.now() + initialSeconds * SECOND_MS)
  const [remaining, setRemaining] = useState(initialSeconds)

  // One self-rescheduling chain for the component's life, cleared on unmount. Not `setInterval`
  // decrementing a counter: that made the displayed number a tally of how many times a timer had
  // fired, which is not elapsed time. A browser throttles a hidden tab's timers to about once a
  // minute, so a user who switched away came back to a lock claiming five minutes left after five
  // minutes had passed — and the «lockout elapsed» effect below never fired. Reading the clock
  // each tick means a dropped or late tick costs display latency, never correctness.
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / SECOND_MS))
      setRemaining(left)
      if (left <= 0) return
      // Aimed at the next whole-second boundary rather than a flat second, so the chain re-syncs
      // to the deadline after any drift instead of compounding it.
      const untilNextBoundary = (deadline - Date.now()) % SECOND_MS || SECOND_MS
      timer = setTimeout(tick, untilNextBoundary)
    }
    timer = setTimeout(tick, (deadline - Date.now()) % SECOND_MS || SECOND_MS)
    return () => clearTimeout(timer)
  }, [deadline])

  // Lockout elapsed → return to the login form. Separate from the ticking effect so "reached zero"
  // is expressed once, as a value, rather than entangled with the interval callback.
  useEffect(() => {
    if (remaining <= 0) {
      onDismiss()
    }
  }, [remaining, onDismiss])

  return (
    <div className="auth-card account-locked-card" data-testid="account-locked-screen">
      <div className="al-icon-badge">
        <PlaceholderImage className="al-icon" />
      </div>
      <h1>{HEADING}</h1>
      <p className="auth-subtitle al-subtitle">{SUBTITLE}</p>
      <div className="al-timer-pill">
        {RETRY_PREFIX}
        <span data-testid="account-locked-countdown">{formatMmSs(remaining)}</span>
      </div>
      <button
        type="button"
        className="al-back-button"
        data-testid="account-locked-back-to-login"
        onClick={onDismiss}
      >
        {BACK_LABEL}
      </button>
    </div>
  )
}
