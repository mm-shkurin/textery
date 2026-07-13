import './LoginForm.css'

export function LoginForm() {
  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
  }

  return (
    <div className="login-card">
      <h1>Вход в Textery AI</h1>
      <form onSubmit={handleSubmit}>
        <div className="login-field">
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            placeholder="email@example.ru"
            autoComplete="username"
            data-testid="login-email-input"
          />
        </div>
        <div className="login-field">
          <label htmlFor="login-password">Пароль</label>
          <input
            id="login-password"
            type="password"
            placeholder="Пароль"
            autoComplete="current-password"
            data-testid="login-password-input"
          />
        </div>
        <button type="submit" className="login-submit" data-testid="login-submit-button">
          Войти
        </button>
      </form>
    </div>
  )
}
