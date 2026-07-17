import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { AuthLoadingIndicator } from './AuthLoadingIndicator'
import { register, type RegisterApiError } from '../api/registerApi'
import { rememberRegistration } from '../utils/registrationHandoff'
import { GENERIC_REGISTER_FAILURE_MESSAGE, isUsableMessage } from '../utils/authMessages'
import {
  CONFIRM_MISMATCH_MESSAGE,
  isConfirmMismatched,
  isPasswordCompliant,
  PASSWORD_POLICY_HINT,
} from '../utils/passwordPolicy'
import './AuthForm.css'
import './RegisterForm.css'

// 'EMAIL_ALREADY_REGISTERED' is what the backend actually sends on 409 — confirmed by curl
// against the live stack on 2026-07-16. This branch previously matched 'EMAIL_ALREADY_EXISTS',
// a code the backend never emits, so the duplicate-email message could never render. Every
// unit test passed throughout, because they all mock registerApi and assert against the
// invented code.
const DUPLICATE_EMAIL_ERROR_CODE = 'EMAIL_ALREADY_REGISTERED'

// Every rejection resolves to user-facing text — silence is an illegal terminal state, the rule
// LoginForm already states and this form was missing. It returned `null` for anything but a
// duplicate email, and the caller's `if (message)` then set nothing: a 500, a dropped connection
// or an INVALID_PASSWORD left the button springing back with no explanation at all, which reads
// as "the click did nothing" and earns a second identical submit.
//
// The duplicate-email message is the server's own (the backend's `message` guarantee covers it,
// and it is the one code whose text is worth quoting). Every other code — including a body that
// arrived without one — falls back to the client-owned generic constant rather than to nothing.
function applyRegisterError(error: unknown): string {
  if (error && typeof error === 'object' && 'errorCode' in error) {
    const apiError = error as RegisterApiError
    if (apiError.errorCode === DUPLICATE_EMAIL_ERROR_CODE && isUsableMessage(apiError.message)) {
      return apiError.message
    }
  }
  return GENERIC_REGISTER_FAILURE_MESSAGE
}

export function RegisterForm() {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [emailError, setEmailError] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState(false)
  const [confirmError, setConfirmError] = useState(false)
  const confirmTouchedRef = useRef(false)
  const emailInputRef = useRef<HTMLInputElement>(null)
  const passwordInputRef = useRef<HTMLInputElement>(null)
  const confirmInputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    setIsSubmitting(true)
    const password = passwordInputRef.current?.value ?? ''
    try {
      const result = await register(
        emailInputRef.current?.value ?? '',
        password,
        confirmInputRef.current?.value ?? '',
      )
      setEmailError(null)
      // Hand the password to /verify so a verified account lands signed in. In memory only, and
      // deliberately NOT in the router state below — see registrationHandoff for why that
      // distinction is the whole point.
      rememberRegistration(result.email, password)
      // The mocked code is carried in router state, not the URL: a query string would land
      // in browser history and server logs, and the notes require treating it as a real
      // credential. `replace` keeps Back from returning to a form whose submit already
      // consumed the email.
      navigate('/verify', {
        replace: true,
        state: { email: result.email, verificationCode: result.verificationCode },
      })
    } catch (error) {
      setEmailError(applyRegisterError(error))
    } finally {
      setIsSubmitting(false)
    }
  }

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
            ref={emailInputRef}
          />
          {emailError && (
            <div
              className="register-hint register-hint-error"
              data-testid="register-email-error"
              role="alert"
            >
              {emailError}
            </div>
          )}
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
        Уже есть аккаунт?{' '}
        <Link to="/login" data-testid="register-login-link">
          Войти
        </Link>
      </p>
    </div>
  )
}
