import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { login } from '../api/loginApi'
import { saveSession } from '../utils/authSession'
import { GENERIC_LOGIN_FAILURE_MESSAGE, isUsableMessage } from '../utils/loginMessages'
import './AuthForm.css'
import './LoginForm.css'

// Every rejection resolves to user-facing text: silence is an illegal terminal state,
// because the error element's mere PRESENCE is an account-enumeration oracle once 5.3
// starts branching on UNVERIFIED. Only a contract-shaped INVALID_CREDENTIALS error
// carrying a usable server-authored message is displayed verbatim — the backend's
// generic-message guarantee covers exactly that string. Everything else (transport
// failure, unknown error code, a malformed message, or one with no visible text) falls
// back to the client-owned generic constant, so the screen always says something and never
// says something the backend's guarantee did not cover.
//
// "Usable" is `isUsableMessage`, shared with loginApi rather than inlined here — a message
// that renders as a blank box is silence just as surely as no element at all, and the two
// layers must not disagree about which values those are.
//
// Later scenarios (5.3 unverified, 5.4 lockout, 5.6 network) branch their distinct
// messages ABOVE this fallback, not through it.
//
// No `as LoginApiError`, for the reason loginApi no longer says `as string`: nothing at run
// time holds a rejection to the declared shape, so the cast narrowed by promise rather than
// by evidence. Each `in` earns the field it reads and `isUsableMessage` earns the string.
// UNVERIFIED is a DIFFERENT action for the user, not a different wording of "sign-in failed":
// their password was right and they must go confirm the code. Rendering the generic constant
// here told them the one thing that is not true. Confirmed live 2026-07-16: an unverified
// account gets 403 `{"error_code":"UNVERIFIED", message}`.
//
// This is deliberately NOT an enumeration leak to be closed: `01_API_Tests.md` 5.1/5.2 have the
// backend answer "not verified" distinctly by design, and UI spec 5.3 requires a distinct
// message. The product intends to distinguish unverified accounts; the client only has to stop
// hiding what the server already said.
const UNVERIFIED_MESSAGE = 'Аккаунт не подтверждён. Введите код подтверждения из письма.'

function hasErrorCode(error: unknown, code: string): boolean {
  return Boolean(error) && typeof error === 'object' && error !== null &&
    'errorCode' in error && error.errorCode === code
}

function applyLoginError(error: unknown): string {
  if (hasErrorCode(error, 'UNVERIFIED')) {
    return UNVERIFIED_MESSAGE
  }
  if (
    hasErrorCode(error, 'INVALID_CREDENTIALS') &&
    error && typeof error === 'object' &&
    'message' in error && isUsableMessage(error.message)
  ) {
    return error.message
  }
  return GENERIC_LOGIN_FAILURE_MESSAGE
}

export function LoginForm() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const emailInputRef = useRef<HTMLInputElement>(null)
  const passwordInputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    setIsSubmitting(true)
    setFormError(null)
    try {
      const session = await login(
        emailInputRef.current?.value ?? '',
        passwordInputRef.current?.value ?? '',
      )
      // A 200 with no usable token is a broken contract, not a successful login. Navigating on
      // it would drop the user into the app with no credential and fail later, somewhere that
      // cannot explain itself.
      if (!session.accessToken) {
        setFormError(GENERIC_LOGIN_FAILURE_MESSAGE)
        return
      }
      if (!saveSession(session)) {
        // Storage refused (private mode, embedded webview). Say so rather than navigating into
        // an app that will behave as if signed out.
        setFormError('Не удалось сохранить сессию — проверьте настройки браузера')
        return
      }
      navigate('/', { replace: true })
    } catch (error) {
      setFormError(applyLoginError(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleToggleShowPassword(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault()
    setShowPassword((current) => !current)
  }

  return (
    <div className="auth-card login-card">
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
          <div data-testid="login-form-error">{formError}</div>
        )}
        <AuthSubmitButton testId="login-submit-button" isSubmitting={isSubmitting}>
          Войти
        </AuthSubmitButton>
        {isSubmitting && <AuthLoadingIndicator testId="login-loading-indicator" />}
      </form>
      <p className="auth-footer-link">
        Нет аккаунта? <Link to="/register" data-testid="login-register-link">Зарегистрироваться</Link>
      </p>
    </div>
  )
}
