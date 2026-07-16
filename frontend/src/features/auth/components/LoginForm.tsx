import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { login, type LoginApiError } from '../api/loginApi'
import { GENERIC_LOGIN_FAILURE_MESSAGE } from '../utils/loginMessages'
import './AuthForm.css'
import './LoginForm.css'

// Every rejection resolves to user-facing text: silence is an illegal terminal state,
// because the error element's mere PRESENCE is an account-enumeration oracle once 5.3
// starts branching on UNVERIFIED. Only a contract-shaped INVALID_CREDENTIALS error
// carrying a usable server-authored message is displayed verbatim — the backend's
// generic-message guarantee covers exactly that string. Everything else (transport
// failure, unknown error code, an empty or malformed message) falls back to the
// client-owned generic constant, so the screen always says something and never says
// something the backend's guarantee did not cover.
//
// Later scenarios (5.3 unverified, 5.4 lockout, 5.6 network) branch their distinct
// messages ABOVE this fallback, not through it.
function applyLoginError(error: unknown): string {
  if (error && typeof error === 'object' && 'errorCode' in error) {
    const apiError = error as LoginApiError
    if (apiError.errorCode === 'INVALID_CREDENTIALS' && typeof apiError.message === 'string' && apiError.message) {
      return apiError.message
    }
  }
  return GENERIC_LOGIN_FAILURE_MESSAGE
}

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const emailInputRef = useRef<HTMLInputElement>(null)
  const passwordInputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    setIsSubmitting(true)
    try {
      await login(emailInputRef.current?.value ?? '', passwordInputRef.current?.value ?? '')
      setFormError(null)
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
