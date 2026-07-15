import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { VerifyCodeForm } from '../VerifyCodeForm'

describe('VerifyCodeForm', () => {
  it('displays six single-digit code inputs', () => {
    renderWithRouter(<VerifyCodeForm />)

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
      renderWithRouter(<VerifyCodeForm />)

      expect(screen.getByTestId('verify-resend-button')).toHaveTextContent(
        'Письмо не пришло? Отправить код повторно',
      )
      expect(screen.getByTestId('verify-resend-countdown')).toHaveTextContent('01:00')
    })
  })

  describe('digit auto-advance focus', () => {
    const expectOtherBoxesEmpty = (exceptIndex: number) => {
      for (let index = 0; index < 6; index += 1) {
        if (index === exceptIndex) continue
        expect((screen.getByTestId(`verify-code-input-${index}`) as HTMLInputElement).value).toBe('')
      }
    }

    it('advances focus to the next box and records the digit when a digit is typed', () => {
      renderWithRouter(<VerifyCodeForm />)

      const firstInput = screen.getByTestId('verify-code-input-0') as HTMLInputElement
      const secondInput = screen.getByTestId('verify-code-input-1')
      firstInput.focus()
      fireEvent.change(firstInput, { target: { value: '5' } })

      expect(firstInput.value).toBe('5')
      expect(document.activeElement).toBe(secondInput)
      expectOtherBoxesEmpty(0)
    })

    it('keeps focus on the last box and records the digit when its value is typed', () => {
      renderWithRouter(<VerifyCodeForm />)

      const lastInput = screen.getByTestId('verify-code-input-5') as HTMLInputElement
      lastInput.focus()
      fireEvent.change(lastInput, { target: { value: '9' } })

      expect(lastInput.value).toBe('9')
      expect(document.activeElement).toBe(lastInput)
      expectOtherBoxesEmpty(5)
    })
  })

  describe('confirm button', () => {
    it('disables the confirm button immediately after click', () => {
      renderWithRouter(<VerifyCodeForm />)
      const confirmButton = screen.getByTestId('verify-confirm-button')
      expect(confirmButton).toHaveTextContent('Подтвердить')
      expect(confirmButton).not.toBeDisabled()

      fireEvent.click(confirmButton)

      expect(confirmButton).toBeDisabled()
    })
  })

  describe('resend action', () => {
    afterEach(() => {
      vi.unstubAllGlobals()
    })

    it('calls the resend-code endpoint with the pending email when clicked', () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ code: '123456' }),
      })
      vi.stubGlobal('fetch', fetchMock)

      renderWithRouter(<VerifyCodeForm email="user@example.com" />)

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
