import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { OAuthProviderButtons } from './OAuthProviderButtons'
import { OAuthErrorBanner } from './OAuthErrorBanner'
import { AccountLockedScreen } from './AccountLockedScreen'
import { useLoginSubmit } from '../hooks/useLoginSubmit'
import { NETWORK_LOGIN_FAILURE_MESSAGE } from '../utils/authMessages'
import './AuthForm.css'
import './AuthStatus.css'
import './LoginForm.css'

// The submit lifecycle — credentials in, one of lockout / network / rejection / success out — is
// in ../hooks/useLoginSubmit; login-rejection interpretation is in ../utils/loginErrorHandling.
// What is left here is markup and the show/hide-password toggle, which is display state and
// nothing else. Lockout is NOT a message branch: it swaps the whole screen, below.
export function LoginForm() {
  const {
    emailInputRef,
    passwordInputRef,
    isSubmitting,
    formError,
    networkError,
    lockoutSeconds,
    dismissLockout,
    handleSubmit,
  } = useLoginSubmit()
  const [showPassword, setShowPassword] = useState(false)

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
