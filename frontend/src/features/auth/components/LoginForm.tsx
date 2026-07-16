import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { login, type LoginApiError } from '../api/loginApi'
import './AuthForm.css'
import './LoginForm.css'

// Only a contract-shaped INVALID_CREDENTIALS error carrying a server-authored message
// becomes user-facing text. Anything else (transport failure, unknown error code, a
// contract error with no message) renders nothing — the login screen never displays a
// string the backend's generic-message guarantee did not cover.
function applyLoginError(error: unknown): string | null {
  if (error && typeof error === 'object' && 'errorCode' in error) {
    const apiError = error as LoginApiError
    if (apiError.errorCode === 'INVALID_CREDENTIALS' && typeof apiError.message === 'string') {
      return apiError.message
    }
  }
  return null
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
