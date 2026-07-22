import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { oauthExchange } from '../api/oauthExchangeApi'
import { saveSession } from '../utils/authSession'
import { safeRedirectTarget } from '../utils/safeRedirectTarget'
import './OAuthCallback.css'

// The /auth/callback interstitial. The visitor arrives here from the provider with a one-time
// handoff `code` in the query; the frontend exchanges it for a session (POST /oauth/exchange),
// stores the tokens, and lands them on the app shell — REPLACING history so Back does not walk
// back onto this transient screen.
//
// Scenario 3.1 (happy path) only. The rich error/replay/network handling is 4.x; here a rejected
// exchange must merely stop the loading state without crashing. FAIL-CLOSED on a refused store:
// if `saveSession` returns false there is no credential, so navigating would strand the user in a
// sign-in loop — mirrors LoginForm's `if (!saveSession(session))` guard.
export function OAuthCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const code = searchParams.get('code') ?? ''
  // The exchange runs once for the mount: a ref guard keeps an effect re-run from firing a second
  // POST / store / navigate, so the "exactly once" contract holds regardless of what re-renders.
  const hasExchanged = useRef(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (hasExchanged.current) return
    hasExchanged.current = true

    let active = true
    oauthExchange({ code })
      .then((session) => {
        if (!active) return
        const stored = saveSession({
          accessToken: session.accessToken,
          refreshToken: session.refreshToken,
        })
        // FAIL-CLOSED: only land on the app shell when a credential was actually stored.
        if (!stored) return
        navigate(safeRedirectTarget(undefined), { replace: true })
      })
      .catch(() => {
        if (active) setFailed(true)
      })

    return () => {
      active = false
    }
  }, [code, navigate])

  if (failed) {
    return (
      <div className="oauth-callback-card" data-testid="oauth-callback-error">
        <h1>Не удалось завершить вход</h1>
        <p className="oauth-callback-subtitle">Попробуйте войти ещё раз.</p>
      </div>
    )
  }

  return (
    <div className="oauth-callback-card" data-testid="oauth-callback-loading">
      <div className="oauth-callback-spinner" aria-hidden="true" />
      <output className="oauth-callback-status" aria-live="polite">
        <h1>Завершаем вход…</h1>
        <p className="oauth-callback-subtitle">Это займёт пару секунд. Не закрывайте страницу.</p>
      </output>
    </div>
  )
}
