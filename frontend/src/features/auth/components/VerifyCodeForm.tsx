import { useRef, useState } from 'react'
import { resendCode } from '../api/authApi'
import { useSubmitPlaceholder } from '../hooks/useSubmitPlaceholder'
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

export function VerifyCodeForm({ email }: VerifyCodeFormProps) {
  const [countdownSeconds] = useState(RESEND_COUNTDOWN_SECONDS)
  const [isResending, setIsResending] = useState(false)
  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(''))
  const inputRefs = useRef<Array<HTMLInputElement | null>>([])
  const { isSubmitting, handleSubmit } = useSubmitPlaceholder()

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
        <button
          type="submit"
          className="auth-submit"
          data-testid="verify-confirm-button"
          disabled={isSubmitting}
        >
          Подтвердить
        </button>
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
