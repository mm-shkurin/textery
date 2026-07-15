import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { useSubmitPlaceholder } from '../hooks/useSubmitPlaceholder'
import {
  CONFIRM_MISMATCH_MESSAGE,
  isConfirmMismatched,
  isPasswordCompliant,
  PASSWORD_POLICY_HINT,
} from '../utils/passwordPolicy'
import './AuthForm.css'
import './RegisterForm.css'

export function RegisterForm() {
  const { isSubmitting, handleSubmit } = useSubmitPlaceholder()
  const [passwordError, setPasswordError] = useState(false)
  const [confirmError, setConfirmError] = useState(false)
  const confirmTouchedRef = useRef(false)
  const passwordInputRef = useRef<HTMLInputElement>(null)
  const confirmInputRef = useRef<HTMLInputElement>(null)

  function handlePasswordBlur(event: React.FocusEvent<HTMLInputElement>) {
    const password = event.target.value
    setPasswordError(password.length > 0 && !isPasswordCompliant(password))

    if (confirmTouchedRef.current) {
      setConfirmError(isConfirmMismatched(password, confirmInputRef.current?.value ?? ''))
    }
  }

  function handleConfirmBlur(event: React.FocusEvent<HTMLInputElement>) {
    confirmTouchedRef.current = true
    setConfirmError(isConfirmMismatched(passwordInputRef.current?.value ?? '', event.target.value))
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
            ref={passwordInputRef}
            onBlur={handlePasswordBlur}
          />
          <div
            className={passwordError ? 'register-hint register-hint-error' : 'register-hint'}
            data-testid={passwordError ? 'register-password-error' : undefined}
          >
            {PASSWORD_POLICY_HINT}
          </div>
        </div>
        <div className="auth-field">
          <label htmlFor="confirm">Повторите пароль</label>
          <input
            id="confirm"
            type="password"
            placeholder="Повторите пароль"
            data-testid="register-confirm-password-input"
            ref={confirmInputRef}
            onBlur={handleConfirmBlur}
          />
          {confirmError && (
            <div className="register-hint register-hint-error" data-testid="register-confirm-error">
              {CONFIRM_MISMATCH_MESSAGE}
            </div>
          )}
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
