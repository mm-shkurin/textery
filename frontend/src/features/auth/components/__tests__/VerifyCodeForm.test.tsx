import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
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

  describe('resend action', () => {
    afterEach(() => {
      vi.unstubAllGlobals()
    })

    it.skip('calls the resend-code endpoint with the pending email when clicked', () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ code: '123456' }),
      })
      vi.stubGlobal('fetch', fetchMock)

      render(
        <MemoryRouter>
          <VerifyCodeForm email="user@example.com" />
        </MemoryRouter>,
      )

      fireEvent.click(screen.getByTestId('verify-resend-button'))

      expect(fetchMock).toHaveBeenCalledTimes(1)
      const [url, init] = fetchMock.mock.calls[0]
      expect(url).toBe('/api/v1/auth/resend-code')
      expect(init.method).toBe('POST')
      expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
      expect(JSON.parse(init.body)).toEqual({ email: 'user@example.com' })
    })
  })
})
