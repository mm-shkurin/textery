import { useState } from 'react'
import './AuthForm.css'
import './VerifyCodeForm.css'

const RESEND_COUNTDOWN_SECONDS = 60

function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export function VerifyCodeForm() {
  const [countdownSeconds] = useState(RESEND_COUNTDOWN_SECONDS)

  return (
    <div className="auth-card verify-code-card">
      <h1>Введите код подтверждения</h1>
      <div className="verify-code-inputs">
        {Array.from({ length: 6 }, (_, index) => (
          <input
            key={index}
            type="text"
            inputMode="numeric"
            maxLength={1}
            data-testid={`verify-code-input-${index}`}
          />
        ))}
      </div>
      <p className="verify-resend">
        <button type="button" data-testid="verify-resend-button">
          Письмо не пришло? Отправить код повторно
        </button>
        <span data-testid="verify-resend-countdown">{formatCountdown(countdownSeconds)}</span>
      </p>
    </div>
  )
}
