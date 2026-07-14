import { useState } from 'react'
import { Link } from 'react-router-dom'
import './AuthForm.css'
import './RegisterForm.css'

const SUBMIT_PLACEHOLDER_DELAY_MS = 500

export function RegisterForm() {
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    try {
      // Placeholder in-flight boundary — no registration API exists yet
      // (backend endpoint is being built in a parallel session; real
      // wiring lands in Scenario 3.1). A real delay is used instead of
      // Promise.resolve() so the disabled window is long enough for
      // Selenium to observe it in a real browser.
      await new Promise((resolve) => setTimeout(resolve, SUBMIT_PLACEHOLDER_DELAY_MS))
    } finally {
      setIsSubmitting(false)
    }
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
        <button
          type="submit"
          className="auth-submit"
          data-testid="register-submit-button"
          disabled={isSubmitting}
        >
          Зарегистрироваться
        </button>
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
