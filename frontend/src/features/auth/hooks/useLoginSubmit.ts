import { useCallback, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { login, type LoginResult } from '../api/loginApi'
import { saveSession } from '../utils/authSession'
import { GENERIC_LOGIN_FAILURE_MESSAGE, SESSION_SAVE_FAILURE_MESSAGE } from '../utils/authMessages'
import {
  isAccountLocked,
  isLoginNetworkError,
  loginErrorMessage,
  readLockoutRetrySeconds,
} from '../utils/loginErrorHandling'
import { safeRedirectTarget } from '../utils/safeRedirectTarget'

// The whole submit lifecycle of the login screen — credentials in, one of four outcomes out —
// lives here rather than in LoginForm so the component is markup plus a state read. The four
// outcomes are genuinely different states, not one message with different text: a lockout swaps
// the screen, a transport failure gets its own retry-capable banner, a rejected credential gets
// the field-level message, and success navigates.
export function useLoginSubmit() {
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = safeRedirectTarget((location.state as { from?: unknown } | null)?.from)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  // A network/transport failure is a DIFFERENT state from a rejected credential: it renders its own
  // retry-capable element, visually distinct from the field-level validation error, so the user is
  // told the connection dropped rather than that their password was wrong.
  const [networkError, setNetworkError] = useState(false)
  // Non-null once the server reports a lockout: the seconds it wants us to wait. Its presence,
  // not a message, is what swaps the whole screen for the account-locked one.
  const [lockoutSeconds, setLockoutSeconds] = useState<number | null>(null)
  const emailInputRef = useRef<HTMLInputElement>(null)
  const passwordInputRef = useRef<HTMLInputElement>(null)

  // Both the countdown elapsing and the user clicking "back to login" return to the form, so both
  // just clear the lockout. Stable identity so the screen's expiry effect doesn't re-run per tick.
  const dismissLockout = useCallback(() => setLockoutSeconds(null), [])

  // ONLY login()'s own rejection may reach here: lockout, transport/network, or a message
  // rejection. A throw from the post-login steps is a LOCAL fault (storage, routing), not a
  // transport failure, and must never be misread as "check your connection" — so it is kept out
  // of this classifier entirely (see the split trys in handleSubmit below).
  function applyLoginFailure(error: unknown) {
    // Lockout is not a message on the form — it replaces the form. Branch it out before the
    // message path so the account-locked screen owns the display (message stays '' from the api).
    if (isAccountLocked(error)) {
      setLockoutSeconds(readLockoutRetrySeconds(error))
      return
    }
    // A transport failure, a client-side timeout (a hung request), or a gateway 5xx is a
    // connection problem, not a bad credential — it gets the distinct, retry-capable
    // network-error state instead of the form-error message.
    if (isLoginNetworkError(error)) {
      setNetworkError(true)
      return
    }
    setFormError(loginErrorMessage(error))
  }

  function finishSignIn(session: LoginResult) {
    // A 200 with no usable token is a broken contract, not a successful login. Navigating on it
    // would drop the user into the app with no credential and fail later, somewhere that cannot
    // explain itself.
    if (!session.accessToken) {
      setFormError(GENERIC_LOGIN_FAILURE_MESSAGE)
      return
    }
    if (!saveSession(session)) {
      // Storage refused (private mode, embedded webview). Say so rather than navigating into an
      // app that will behave as if signed out.
      setFormError(SESSION_SAVE_FAILURE_MESSAGE)
      return
    }
    navigate(redirectTo, { replace: true })
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    setIsSubmitting(true)
    setFormError(null)
    setNetworkError(false)
    // Wide finally: isSubmitting resets on EVERY exit path — a login rejection, a post-login
    // throw, or success — so the spinner never strands and the submit button always re-enables.
    try {
      let session: LoginResult
      try {
        session = await login(
          emailInputRef.current?.value ?? '',
          passwordInputRef.current?.value ?? '',
        )
      } catch (error) {
        applyLoginFailure(error)
        return
      }
      // Post-login is a SEPARATE concern from login()'s transport outcome: a throw here
      // (saveSession/navigate faulting) is a local bug, so it earns the generic login-failure
      // message — user feedback, not a silent swallow — and never the network banner.
      try {
        finishSignIn(session)
      } catch {
        setFormError(GENERIC_LOGIN_FAILURE_MESSAGE)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    emailInputRef,
    passwordInputRef,
    isSubmitting,
    formError,
    networkError,
    lockoutSeconds,
    dismissLockout,
    handleSubmit,
  }
}
