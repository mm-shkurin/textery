import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { resendCode } from '../api/authApi'
import { verify } from '../api/verifyApi'
import { AuthSubmitButton } from './AuthSubmitButton'
import { CODE_LENGTH, VerifyCodeInputs } from './VerifyCodeInputs'
import { useResendCountdown } from '../hooks/useResendCountdown'
import { signInAfterVerification } from '../utils/postVerifySignIn'
import { GENERIC_VERIFY_FAILURE_MESSAGE } from '../utils/authMessages'
import { verifyErrorMessage } from '../utils/verifyErrorHandling'
import './AuthForm.css'
import './VerifyCodeForm.css'

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
const MISSING_EMAIL_MESSAGE = 'Не найден email для подтверждения — начните регистрацию заново'

// Rejection interpretation (wrong-code distinct message, usable-server-message pass-through,
// generic fallback) lives in ../utils/verifyErrorHandling so this component stays under the
// 200-line cap and mirrors login's loginErrorHandling.
export function VerifyCodeForm({ email: emailProp }: VerifyCodeFormProps) {
  const navigate = useNavigate()
  const routerState = (useLocation().state ?? {}) as VerifyRouterState
  const email = emailProp ?? routerState.email
  const mockedCode = routerState.verificationCode
  const countdown = useResendCountdown()
  const [isResending, setIsResending] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [isVerified, setIsVerified] = useState(false)
  const [codeError, setCodeError] = useState(false)
  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(''))

  // Editing the code clears the error paint — the boxes no longer show the value the server
  // rejected, so keeping them red would accuse input the user has already changed.
  function handleDigitsChange(next: string[]) {
    setDigits(next)
    if (codeError) setCodeError(false)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    if (!email) {
      setFormError(MISSING_EMAIL_MESSAGE)
      return
    }
    setIsSubmitting(true)
    try {
      const result = await verify(email, digits.join(''))
      setFormError(null)
      setCodeError(false)
      setIsVerified(result.isVerified)
      // A 200 that says `is_verified: false` is not a success to navigate on. The backend has
      // never sent one, but the field only means something if we read it — treating any 200 as
      // "verified" would make the flag decoration.
      if (!result.isVerified) {
        setFormError(GENERIC_VERIFY_FAILURE_MESSAGE)
        setCodeError(true)
        return
      }
      // Verification does not mint a session, so getting into the app is a separate step that
      // can land in two places. Whatever it decides, the user leaves this screen: staying put
      // after a successful confirm is what made this form look hung.
      navigate(await signInAfterVerification(email), { replace: true })
    } catch (error) {
      setIsVerified(false)
      setFormError(verifyErrorMessage(error))
      setCodeError(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleResend() {
    if (!email || !countdown.isElapsed) return
    setIsResending(true)
    setFormError(null)
    try {
      await resendCode(email)
      // Only a resend that actually happened restarts the wait. Restarting on a failure would
      // lock the user out of retrying for a minute over a request the server never accepted.
      countdown.restart()
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
        <VerifyCodeInputs digits={digits} onChange={handleDigitsChange} hasError={codeError} />
        <AuthSubmitButton testId="verify-confirm-button" isSubmitting={isSubmitting}>
          Подтвердить
        </AuthSubmitButton>
        {formError && (
          <div className="auth-form-error" data-testid="verify-form-error" role="alert">
            {formError}
          </div>
        )}
        {isVerified && (
          // <output> carries role="status" implicitly — the markup says what it is.
          <output className="auth-form-success" data-testid="verify-success">
            Аккаунт подтверждён
          </output>
        )}
      </form>
      <p className="verify-resend">
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
