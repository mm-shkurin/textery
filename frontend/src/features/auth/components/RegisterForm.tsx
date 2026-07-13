import './RegisterForm.css'

export function RegisterForm() {
  return (
    <div className="register-card">
      <h1>Регистрация в Textery AI</h1>
      <p className="register-subtitle">
        Создайте аккаунт по email, чтобы начать генерировать документы
      </p>
      <form>
        <div className="register-field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="email@example.ru"
            data-testid="register-email-input"
          />
        </div>
        <div className="register-field">
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
        <div className="register-field">
          <label htmlFor="confirm">Повторите пароль</label>
          <input
            id="confirm"
            type="password"
            placeholder="Повторите пароль"
            data-testid="register-confirm-password-input"
          />
        </div>
        <button type="submit" className="register-submit" data-testid="register-submit-button">
          Зарегистрироваться
        </button>
        <p className="register-terms">
          Создавая аккаунт, вы соглашаетесь с нашими Условиями использования, Политикой
          конфиденциальности и Обработкой персональных данных
        </p>
      </form>
      <p className="register-footer-link">
        Уже есть аккаунт? <a href="/login">Войти</a>
      </p>
    </div>
  )
}
