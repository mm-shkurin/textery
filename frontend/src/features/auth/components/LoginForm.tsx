import { useCallback, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { OAuthProviderButtons } from './OAuthProviderButtons'
import { OAuthErrorBanner } from './OAuthErrorBanner'
import { AccountLockedScreen } from './AccountLockedScreen'
import { login, type LoginResult } from '../api/loginApi'
import { saveSession } from '../utils/authSession'
import {
  GENERIC_LOGIN_FAILURE_MESSAGE,
  NETWORK_LOGIN_FAILURE_MESSAGE,
  SESSION_SAVE_FAILURE_MESSAGE,
} from '../utils/authMessages'
import {
  isAccountLocked,
  isLoginNetworkError,
  loginErrorMessage,
  readLockoutRetrySeconds,
} from '../utils/loginErrorHandling'
import { safeRedirectTarget } from '../utils/safeRedirectTarget'
import './AuthForm.css'
import './LoginForm.css'

// Login-rejection interpretation (UNVERIFIED distinct message, INVALID_CREDENTIALS pass-through,
// lockout detection, Retry-After extraction) lives in ../utils/loginErrorHandling so this component
// stays under the 200-line cap. Lockout is NOT a message branch: it swaps the whole screen, below.

export function LoginForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = safeRedirectTarget((location.state as { from?: unknown } | null)?.from)
  const [showPassword, setShowPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  // A network/transport failure is a DIFFERENT state from a rejected credential: it renders its own
  // retry-capable element, visually distinct from the field-level validation error, so the user is
  // told the connection dropped rather than that their password was wrong.
  const [networkError, setNetworkError] = useState(false)
  // Non-null once the server reports a lockout: the seconds it wants us to wait. Its presence,
  // not a message, is what swaps the whole screen for the account-locked one below.
  const [lockoutSeconds, setLockoutSeconds] = useState<number | null>(null)
  const emailInputRef = useRef<HTMLInputElement>(null)
  const passwordInputRef = useRef<HTMLInputElement>(null)

  // Both the countdown elapsing and the user clicking "back to login" return to the form, so both
  // just clear the lockout. Stable identity so the screen's expiry effect doesn't re-run per tick.
  const dismissLockout = useCallback(() => setLockoutSeconds(null), [])

  // ONLY login()'s own rejection may reach here: lockout, transport/network, or a message
  // rejection. A throw from the post-login steps is a LOCAL fault (storage, routing), not a
  // transport failure, and must never be misread as "check your connection" — so it is kept out
  // of this classifier entirely (see handleSubmit's split trys below).
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

  function handleToggleShowPassword(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault()
    setShowPassword((current) => !current)
  }

  if (lockoutSeconds !== null) {
    return <AccountLockedScreen retryAfterSeconds={lockoutSeconds} onDismiss={dismissLockout} />
  }

  return (
    <div className="auth-card login-card">
      <OAuthErrorBanner />
      <h1>Вход в Textery AI</h1>
      <p className="auth-subtitle login-subtitle">Введите свои данные для продолжения работы</p>
      <form onSubmit={handleSubmit}>
        <div className="auth-field">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            placeholder="email@example.ru"
            autoComplete="username"
            data-testid="login-email-input"
            ref={emailInputRef}
          />
        </div>
        <div className="auth-field">
          <label htmlFor="login-password">Пароль</label>
          <div className="auth-field-wrap">
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Пароль"
              autoComplete="current-password"
              data-testid="login-password-input"
              ref={passwordInputRef}
            />
            <button
              type="button"
              className="auth-password-toggle"
              data-testid="login-password-toggle"
              aria-pressed={showPassword}
              onClick={handleToggleShowPassword}
            >
              {showPassword ? 'Скрыть' : 'Показать'}
            </button>
          </div>
        </div>
        {formError && (
          // role="alert" because this text is the whole point of the submit failing: a sighted
          // user sees it appear, and without the live region a screen-reader user gets nothing
          // but a button that re-enabled. The one error the module comments most insist must
          // reach the user was the one not announced.
          <div className="auth-form-error" data-testid="login-form-error" role="alert">
            {formError}
          </div>
        )}
        {networkError && (
          // A distinct element (own class, own testid) from the validation error above: this is a
          // connection problem, not a rejected credential, so it must not be mistaken for either
          // one by a sighted or a screen-reader user. role="alert" announces it; the copy invites a
          // retry, and the submit button re-enables (finally clears isSubmitting) so the user can.
          <div className="auth-network-error" data-testid="login-network-error" role="alert">
            {NETWORK_LOGIN_FAILURE_MESSAGE}
          </div>
        )}
        <AuthSubmitButton testId="login-submit-button" isSubmitting={isSubmitting}>
          Войти
        </AuthSubmitButton>
        {isSubmitting && <AuthLoadingIndicator testId="login-loading-indicator" />}
      </form>
      <OAuthProviderButtons />
      <p className="auth-footer-link">
        Нет аккаунта?{' '}
        <Link to="/register" data-testid="login-register-link">
          Зарегистрироваться
        </Link>
      </p>
    </div>
  )
}
