import { Link } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { useSubmitPlaceholder } from '../hooks/useSubmitPlaceholder'
import './AuthForm.css'
import './RegisterForm.css'

export function RegisterForm() {
  const { isSubmitting, handleSubmit } = useSubmitPlaceholder()

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
          />
          <div className="register-hint">
            Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол
          </div>
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
        {isSubmitting && (
          <div
            className="auth-loading-indicator"
            data-testid="register-loading-indicator"
            role="status"
            aria-live="polite"
          >
            Загрузка...
          </div>
        )}
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
