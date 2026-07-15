import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { useSubmitPlaceholder } from '../hooks/useSubmitPlaceholder'
import { isPasswordCompliant, PASSWORD_POLICY_HINT } from '../hooks/passwordPolicy'
import './AuthForm.css'
import './RegisterForm.css'

export function RegisterForm() {
  const { isSubmitting, handleSubmit } = useSubmitPlaceholder()
  const [passwordError, setPasswordError] = useState(false)

  function handlePasswordBlur(event: React.FocusEvent<HTMLInputElement>) {
    setPasswordError(event.target.value.length > 0 && !isPasswordCompliant(event.target.value))
  }

  return (
    <div className="auth-card register-card">
      <h1>Регистрация в Textery AI</h1>
      <p className="auth-subtitle register-subtitle">
        Создайте аккаунт по email, чтобы начать генерировать документы
      </p>
      <form onSubmit={handleSubmit}>
        <div className="auth-field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="email@example.ru"
            data-testid="register-email-input"
          />
        </div>
        <div className="auth-field">
          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            type="password"
            placeholder="Минимум 8 символов"
            data-testid="register-password-input"
            onBlur={handlePasswordBlur}
          />
          {passwordError ? (
            <div className="register-hint register-hint-error" data-testid="register-password-error">
              {PASSWORD_POLICY_HINT}
            </div>
          ) : (
            <div className="register-hint">{PASSWORD_POLICY_HINT}</div>
          )}
        </div>
        <div className="auth-field">
          <label htmlFor="confirm">Повторите пароль</label>
          <input
            id="confirm"
            type="password"
            placeholder="Повторите пароль"
            data-testid="register-confirm-password-input"
          />
        </div>
        <AuthSubmitButton testId="register-submit-button" isSubmitting={isSubmitting}>
          Зарегистрироваться
        </AuthSubmitButton>
        {isSubmitting && <AuthLoadingIndicator testId="register-loading-indicator" />}
        <p className="register-terms">
          Создавая аккаунт, вы соглашаетесь с нашими Условиями использования, Политикой
          конфиденциальности и Обработкой персональных данных
        </p>
      </form>
      <p className="auth-footer-link">
        Уже есть аккаунт? <Link to="/login">Войти</Link>
      </p>
    </div>
  )
}
