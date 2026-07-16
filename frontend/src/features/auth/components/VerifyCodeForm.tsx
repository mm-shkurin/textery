import { useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { resendCode } from '../api/authApi'
import { verify, type VerifyApiError, GENERIC_VERIFY_FAILURE_MESSAGE } from '../api/verifyApi'
import { AuthSubmitButton } from './AuthSubmitButton'
import './AuthForm.css'
import './VerifyCodeForm.css'

const RESEND_COUNTDOWN_SECONDS = 60
const CODE_LENGTH = 6

function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export interface VerifyCodeFormProps {
  email?: string
}

// Register hands the email and the mocked code over in router state (see RegisterForm).
// The prop remains for tests and for direct composition.
interface VerifyRouterState {
  email?: string
  verificationCode?: string
}

function applyVerifyError(error: unknown): string {
  if (error && typeof error === 'object' && 'errorCode' in error) {
    const apiError = error as VerifyApiError
    if (typeof apiError.message === 'string' && apiError.message.trim()) {
      return apiError.message
    }
  }
  return GENERIC_VERIFY_FAILURE_MESSAGE
}

export function VerifyCodeForm({ email: emailProp }: VerifyCodeFormProps) {
  const routerState = (useLocation().state ?? {}) as VerifyRouterState
  const email = emailProp ?? routerState.email
  const mockedCode = routerState.verificationCode
  const [countdownSeconds] = useState(RESEND_COUNTDOWN_SECONDS)
  const [isResending, setIsResending] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [isVerified, setIsVerified] = useState(false)
  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(''))
  const inputRefs = useRef<Array<HTMLInputElement | null>>([])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    if (!email) {
      setFormError('Не найден email для подтверждения — начните регистрацию заново')
      return
    }
    setIsSubmitting(true)
    try {
      const result = await verify(email, digits.join(''))
      setFormError(null)
      setIsVerified(result.isVerified)
    } catch (error) {
      setIsVerified(false)
      setFormError(applyVerifyError(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleDigitChange(index: number, value: string) {
    setDigits((previous) => {
      const next = [...previous]
      next[index] = value
      return next
    })

    if (value && index < CODE_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus()
    }
  }

  async function handleResend() {
    if (!email) return
    setIsResending(true)
    try {
      await resendCode(email)
    } catch {
      // Resend failures are non-fatal here; a dedicated error UI is out of scope for this step.
    } finally {
      setIsResending(false)
    }
  }

  return (
    <div className="auth-card verify-code-card">
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
        <div className="verify-code-inputs">
          {Array.from({ length: CODE_LENGTH }, (_, index) => (
            <input
              key={index}
              ref={(element) => {
                inputRefs.current[index] = element
              }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digits[index]}
              onChange={(event) => handleDigitChange(index, event.target.value)}
              data-testid={`verify-code-input-${index}`}
            />
          ))}
        </div>
        <AuthSubmitButton testId="verify-confirm-button" isSubmitting={isSubmitting}>
          Подтвердить
        </AuthSubmitButton>
        {formError && (
          <div className="verify-form-error" data-testid="verify-form-error" role="alert">
            {formError}
          </div>
        )}
        {isVerified && (
          <div className="verify-success" data-testid="verify-success" role="status">
            Аккаунт подтверждён
          </div>
        )}
      </form>
      <p className="verify-resend">
        <span data-testid="verify-resend-countdown">{formatCountdown(countdownSeconds)}</span>
        <button
          type="button"
          data-testid="verify-resend-button"
          disabled={isResending}
          onClick={handleResend}
        >
          Письмо не пришло? Отправить код повторно
        </button>
      </p>
    </div>
  )
}
