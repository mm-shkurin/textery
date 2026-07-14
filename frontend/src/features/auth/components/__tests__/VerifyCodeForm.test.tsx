import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { VerifyCodeForm } from '../VerifyCodeForm'

describe('VerifyCodeForm', () => {
  it('displays six single-digit code inputs', () => {
    render(
      <MemoryRouter>
        <VerifyCodeForm />
      </MemoryRouter>,
    )

    for (let index = 0; index < 6; index += 1) {
      const input = screen.getByTestId(`verify-code-input-${index}`)
      expect(input).toHaveAttribute('type', 'text')
      expect(input).toHaveAttribute('inputMode', 'numeric')
      expect(input).toHaveAttribute('maxLength', '1')
    }
  })

  describe('resend countdown', () => {
    // Fixed system clock: the countdown is a live timer (setInterval/Date-based),
    // so asserting its text against real wall-clock time is a race (the same
    // risk flagged for verify_code_page_statements.py's Selenium assertion).
    // Fake timers pin "now" so the initial render value is deterministic and
    // asserting immediately after render can never observe a tick-down.
    beforeEach(() => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-07-14T00:00:00.000Z'))
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('displays a resend action with an initial countdown of 01:00', () => {
      render(
        <MemoryRouter>
          <VerifyCodeForm />
        </MemoryRouter>,
      )

      expect(screen.getByTestId('verify-resend-button')).toHaveTextContent(
        'Письмо не пришло? Отправить код повторно',
      )
      expect(screen.getByTestId('verify-resend-countdown')).toHaveTextContent('01:00')
    })
  })
})
