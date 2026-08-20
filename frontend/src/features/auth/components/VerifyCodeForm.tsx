import { useLocation } from 'react-router-dom'
import { AuthSubmitButton } from './AuthSubmitButton'
import { VerifyCodeInputs } from './VerifyCodeInputs'
import { useVerifyCode } from '../hooks/useVerifyCode'
import authFormStyles from './AuthForm.module.css'
import authStatusStyles from './AuthStatus.module.css'
import styles from './VerifyCodeForm.module.css'

export interface VerifyCodeFormProps {
  email?: string
}

// Register hands the email and the mocked code over in router state (see RegisterForm).
// The prop remains for tests and for direct composition.
interface VerifyRouterState {
  email?: string
  verificationCode?: string
}

// Markup plus a state read. The confirm, the resend and the code on display are one state machine
// and live in useVerifyCode; what is left here is which of them the screen shows.
export function VerifyCodeForm({ email: emailProp }: VerifyCodeFormProps) {
  const routerState = (useLocation().state ?? {}) as VerifyRouterState
  const {
    mockedCode,
    digits,
    codeError,
    formError,
    isVerified,
    isSubmitting,
    isResending,
    countdown,
    handleDigitsChange,
    handleSubmit,
    handleResend,
  } = useVerifyCode(emailProp ?? routerState.email, routerState.verificationCode)

  return (
    <div className={`${authFormStyles['auth-card']} verify-code-card`}>
      <h1>Введите код подтверждения</h1>
      {mockedCode && (
        // Required by 07_Authorization_Notes.md: no email is sent, so the screen must show
        // the code outright and say why, or testers are left with no way in. Shown, not
        // pre-filled — the field still exercises the real input path.
        <p className="verify-dev-code" data-testid="verify-dev-code">
          Ваш код: <strong>{mockedCode}</strong> (dev-режим, письмо не отправляется)
        </p>
      )}
      <form onSubmit={handleSubmit}>
        <VerifyCodeInputs digits={digits} onChange={handleDigitsChange} hasError={codeError} />
        <AuthSubmitButton testId="verify-confirm-button" isSubmitting={isSubmitting}>
          Подтвердить
        </AuthSubmitButton>
        {formError && (
          <div
            className={authStatusStyles['auth-form-error']}
            data-testid="verify-form-error"
            role="alert"
          >
            {formError}
          </div>
        )}
        {isVerified && (
          // <output> carries role="status" implicitly — the markup says what it is.
          <output className={authStatusStyles['auth-form-success']} data-testid="verify-success">
            Аккаунт подтверждён
          </output>
        )}
      </form>
      <p className={`${authFormStyles['verify-resend']} ${styles['verify-resend']}`}>
        <span data-testid="verify-resend-countdown">{countdown.formatted}</span>
        <button
          type="button"
          data-testid="verify-resend-button"
          disabled={isResending || !countdown.isElapsed}
          onClick={handleResend}
        >
          Письмо не пришло? Отправить код повторно
        </button>
      </p>
    </div>
  )
}
