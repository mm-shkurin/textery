import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { oauthExchange } from '../api/oauthExchangeApi'
import { isAuthenticated, saveSession } from '../utils/authSession'
import { oauthProviderFailureMessage } from '../utils/oauthMessages'
import { safeRedirectTarget } from '../utils/safeRedirectTarget'
import './AuthForm.css'
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
  // Checked BEFORE the code/exchange path: a provider error or user-cancel arrives as `?error=…`
  // with NO spendable code, so the exchange must never fire. When present we route straight back to
  // /login carrying a provider-aware distinct message (mapped from copy, never the raw value).
  const error = searchParams.get('error')
  const provider = searchParams.get('provider')
  const code = searchParams.get('code') ?? ''
  // The exchange runs once for the mount: a ref guard keeps an effect re-run from firing a second
  // POST / store / navigate, so the "exactly once" contract holds regardless of what re-renders.
  const hasExchanged = useRef(false)
  // Whether the component is currently mounted. A SHARED ref (not a per-effect-run local flag)
  // that survives StrictMode's mount → cleanup → remount replay: the cleanup of run 1 flips it
  // false, the remount of run 2 flips it back true, so the in-flight exchange's `.then`/`.catch`
  // still see `true` and complete the sign-in. On a genuine unmount it stays false, so no
  // post-unmount setState/navigate fires. A per-run local flag would be disarmed by run 1's
  // cleanup and never re-armed for the surviving run → eternal spinner.
  const mountedRef = useRef(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (hasExchanged.current) return
    hasExchanged.current = true

    // Guard order matters: an `?error` param means the provider refused (or the user cancelled) and
    // there is no code to spend — route back to /login with the provider-aware message and fire NO
    // exchange, exactly once. Only the no-error path reaches the exchange below.
    if (error !== null) {
      navigate('/login', {
        replace: true,
        state: { oauthError: oauthProviderFailureMessage(provider) },
      })
      return
    }

    oauthExchange({ code })
      .then((session) => {
        if (!mountedRef.current) return
        const stored = saveSession({
          accessToken: session.accessToken,
          refreshToken: session.refreshToken,
        })
        // FAIL-CLOSED: only land on the app shell when a credential was actually stored. A refused
        // store (Safari private mode / storage-disabled webview) must show a terminal error, NOT
        // hang the spinner forever — skipping only the navigation would strand the user on
        // "Завершаем вход…" indefinitely.
        if (!stored) {
          setFailed(true)
          return
        }
        navigate(safeRedirectTarget(undefined), { replace: true })
      })
      .catch(() => {
        if (!mountedRef.current) return
        // A late/duplicate rejection after a session was already stored (a genuine remount fires a
        // second POST with the spent one-time code) must NOT bounce an already-signed-in user onto
        // the error screen — spec 16_OAuthSignin.md:49-50 / Notes:48-50: "ignored, not a bounce
        // back to login".
        if (isAuthenticated()) {
          navigate(safeRedirectTarget(undefined), { replace: true })
          return
        }
        setFailed(true)
      })
  }, [code, error, provider, navigate])

  // On the error path we route away immediately; render nothing so the transient loading spinner
  // never persists (the visitor is sent to /login, not stranded on "Завершаем вход…").
  if (error !== null) {
    return null
  }

  if (failed) {
    return (
      <div className="auth-card oauth-callback-card" data-testid="oauth-callback-error">
        <h1>Не удалось завершить вход</h1>
        <p className="auth-subtitle oauth-callback-subtitle">Попробуйте войти ещё раз.</p>
      </div>
    )
  }

  return (
    <div className="auth-card oauth-callback-card" data-testid="oauth-callback-loading">
      <div className="oauth-callback-spinner" aria-hidden="true" />
      <output className="oauth-callback-status" aria-live="polite">
        <h1>Завершаем вход…</h1>
        <p className="auth-subtitle oauth-callback-subtitle">
          Это займёт пару секунд. Не закрывайте страницу.
        </p>
      </output>
    </div>
  )
}
