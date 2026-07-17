import { useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { resendCode } from '../api/authApi'
import { verify, type VerifyApiError } from '../api/verifyApi'
import { AuthSubmitButton } from './AuthSubmitButton'
import { signInAfterVerification } from '../utils/postVerifySignIn'
import { GENERIC_VERIFY_FAILURE_MESSAGE, isUsableMessage } from '../utils/authMessages'
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

const RESEND_FAILURE_MESSAGE = 'Не удалось отправить код повторно. Попробуйте ещё раз позже.'

function applyVerifyError(error: unknown): string {
  if (error && typeof error === 'object' && 'errorCode' in error) {
    const apiError = error as VerifyApiError
    if (isUsableMessage(apiError.message)) {
      return apiError.message
    }
  }
  return GENERIC_VERIFY_FAILURE_MESSAGE
}

export function VerifyCodeForm({ email: emailProp }: VerifyCodeFormProps) {
  const navigate = useNavigate()
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
      // A 200 that says `is_verified: false` is not a success to navigate on. The backend has
      // never sent one, but the field only means something if we read it — treating any 200 as
      // "verified" would make the flag decoration.
      if (!result.isVerified) {
        setFormError(GENERIC_VERIFY_FAILURE_MESSAGE)
        return
      }
      // Verification does not mint a session, so getting into the app is a separate step that
      // can land in two places. Whatever it decides, the user leaves this screen: staying put
      // after a successful confirm is what made this form look hung.
      navigate(await signInAfterVerification(email), { replace: true })
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
    setFormError(null)
    try {
      await resendCode(email)
    } catch {
      // Swallowing this made the button a no-op that LOOKS like it worked: the user waits for a
      // code that was never issued, and blames the mail that never arrives. Saying "it failed"
      // is worth more than a tidy screen — they can retry, or go back and register again.
      //
      // Today it always fails: `POST /api/v1/auth/resend-code` is 404, the route does not exist
      // on the backend (verified 2026-07-17 — its OpenAPI document lists register/verify/login/
      // refresh and nothing else) even though endpoints.md specifies it. This makes that gap
      // visible instead of hiding it behind a spinner that resolves to nothing.
      //
      // The status code stays out of the copy on purpose — "HTTP 404" is a fact about our
      // deployment, not a thing the user can act on.
      setFormError(RESEND_FAILURE_MESSAGE)
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
