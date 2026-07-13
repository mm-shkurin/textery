import { Link } from 'react-router-dom'
import './AuthForm.css'
import './LoginForm.css'

export function LoginForm() {
  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
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
          <input
            id="login-password"
            type="password"
            placeholder="Пароль"
            autoComplete="current-password"
            data-testid="login-password-input"
          />
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
