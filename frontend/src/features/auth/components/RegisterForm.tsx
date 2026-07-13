export function RegisterForm() {
  return (
    <form>
      <div className="field">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          placeholder="email@example.ru"
          data-testid="register-email-input"
        />
      </div>
      <div className="field">
        <label htmlFor="password">Пароль</label>
        <input
          id="password"
          type="password"
          placeholder="Минимум 8 символов"
          data-testid="register-password-input"
        />
      </div>
      <div className="field">
        <label htmlFor="confirm">Повторите пароль</label>
        <input
          id="confirm"
          type="password"
          placeholder="Повторите пароль"
          data-testid="register-confirm-password-input"
        />
      </div>
      <button type="submit" data-testid="register-submit-button">
        Зарегистрироваться
      </button>
    </form>
  )
}
