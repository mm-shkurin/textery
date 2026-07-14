import { useState } from 'react'
import { Link } from 'react-router-dom'
import './AuthForm.css'
import './LoginForm.css'

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false)

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
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
        <button type="submit" className="auth-submit" data-testid="login-submit-button">
          Войти
        </button>
      </form>
      <p className="auth-footer-link">
        Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
      </p>
    </div>
  )
}
