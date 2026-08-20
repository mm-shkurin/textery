import { Link } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { useRegisterSubmit } from '../hooks/useRegisterSubmit'
import { CONFIRM_MISMATCH_MESSAGE, PASSWORD_POLICY_HINT } from '../utils/passwordPolicy'
import authFormStyles from './AuthForm.module.css'
import './AuthStatus.module.css'
import styles from './RegisterForm.module.css'

export function RegisterForm() {
  const {
    emailInputRef,
    passwordInputRef,
    confirmInputRef,
    isSubmitting,
    emailError,
    passwordError,
    confirmError,
    markDirty,
    handleSubmit,
    handlePasswordBlur,
    handleConfirmBlur,
    handleLeaveClick,
  } = useRegisterSubmit()

  return (
    <div className={`${authFormStyles['auth-card']} ${styles['register-card']}`}>
      <h1>Регистрация в Textery AI</h1>
      <p className={`${authFormStyles['auth-subtitle']} ${styles['register-subtitle']}`}>
        Создайте аккаунт по email, чтобы начать генерировать документы
      </p>
      <form onSubmit={handleSubmit}>
        <div className={authFormStyles['auth-field']}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="email@example.ru"
            data-testid="register-email-input"
            ref={emailInputRef}
            onChange={markDirty}
          />
          {emailError && (
            <div
              className={`${styles['register-hint']} ${styles['register-hint-error']}`}
              data-testid="register-email-error"
              role="alert"
            >
              {emailError}
            </div>
          )}
        </div>
        <div className={authFormStyles['auth-field']}>
          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            type="password"
            placeholder="Минимум 8 символов"
            data-testid="register-password-input"
            ref={passwordInputRef}
            onChange={markDirty}
            onBlur={handlePasswordBlur}
          />
          {/* The same element is the policy hint and, once blurred non-compliant, the error. It is
              always in the DOM, so `role="alert"` would announce the hint on first paint — hence
              the role appears only in the error state, where it is an alert and not a caption. */}
          <div
            className={
              passwordError
                ? `${styles['register-hint']} ${styles['register-hint-error']}`
                : styles['register-hint']
            }
            data-testid={passwordError ? 'register-password-error' : undefined}
            role={passwordError ? 'alert' : undefined}
          >
            {PASSWORD_POLICY_HINT}
          </div>
        </div>
        <div className={authFormStyles['auth-field']}>
          <label htmlFor="confirm">Повторите пароль</label>
          <input
            id="confirm"
            type="password"
            placeholder="Повторите пароль"
            data-testid="register-confirm-password-input"
            ref={confirmInputRef}
            onChange={markDirty}
            onBlur={handleConfirmBlur}
          />
          {/* role="alert" for the same reason the email error carries one: a mismatch surfaces on
              blur, far from the caret, and a screen-reader user gets no other signal that the two
              passwords disagree. It was the one validation error of the three announcing nothing. */}
          {confirmError && (
            <div
              className={`${styles['register-hint']} ${styles['register-hint-error']}`}
              data-testid="register-confirm-error"
              role="alert"
            >
              {CONFIRM_MISMATCH_MESSAGE}
            </div>
          )}
        </div>
        <AuthSubmitButton testId="register-submit-button" isSubmitting={isSubmitting}>
          Зарегистрироваться
        </AuthSubmitButton>
        {isSubmitting && <AuthLoadingIndicator testId="register-loading-indicator" />}
        <p className={styles['register-terms']}>
          Создавая аккаунт, вы соглашаетесь с нашими Условиями использования, Политикой
          конфиденциальности и Обработкой персональных данных
        </p>
      </form>
      <p className={authFormStyles['auth-footer-link']}>
        Уже есть аккаунт?{' '}
        <Link to="/login" data-testid="register-login-link" onClick={handleLeaveClick}>
          Войти
        </Link>
      </p>
    </div>
  )
}
