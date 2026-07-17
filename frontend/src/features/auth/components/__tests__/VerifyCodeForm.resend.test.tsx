import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { VerifyCodeForm } from '../VerifyCodeForm'
import { RESEND_COUNTDOWN_SECONDS } from '../../hooks/useResendCountdown'

// The resend half of VerifyCodeForm: the countdown and the button it gates. Split out when the
// single test file passed the 200-line limit — these share a concern (and fake timers) that the
// input/submit tests next door do not need at all.
describe('VerifyCodeForm resend', () => {
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

  describe('resend action', () => {
    afterEach(() => {
      vi.unstubAllGlobals()
      vi.useRealTimers()
    })

    // The countdown gates the button, so every resend test has to reach zero first. Fake timers
    // rather than a 60-second wait; `act` because the ticks are setState from a timeout.
    async function elapseCountdown() {
      await act(async () => {
        vi.advanceTimersByTime(RESEND_COUNTDOWN_SECONDS * 1000)
      })
    }

    it('does not call the resend-code endpoint while the countdown is still running', () => {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)

      renderWithRouter(<VerifyCodeForm email="user@example.com" />)

      // The button is disabled, and the handler refuses independently — the countdown is the
      // rule, not the styling. Before this, the button ignored the countdown entirely and a
      // click at 01:00 sent the request.
      expect(screen.getByTestId('verify-resend-button')).toBeDisabled()
      fireEvent.click(screen.getByTestId('verify-resend-button'))
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('counts the countdown down to 00:00 and then enables the resend button', async () => {
      vi.useFakeTimers()
      renderWithRouter(<VerifyCodeForm email="user@example.com" />)

      // Pins that the clock RUNS. It previously rendered 01:00 forever: `useState(60)` with no
      // setter and no timer, so this assertion would have failed at every point in time.
      expect(screen.getByTestId('verify-resend-countdown')).toHaveTextContent('01:00')

      await act(async () => {
        vi.advanceTimersByTime(15_000)
      })
      expect(screen.getByTestId('verify-resend-countdown')).toHaveTextContent('00:45')

      await elapseCountdown()
      expect(screen.getByTestId('verify-resend-countdown')).toHaveTextContent('00:00')
      expect(screen.getByTestId('verify-resend-button')).toBeEnabled()
    })

    it('calls the resend-code endpoint with the pending email once the countdown elapses', async () => {
      vi.useFakeTimers()
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ code: '123456' }),
      })
      vi.stubGlobal('fetch', fetchMock)

      renderWithRouter(<VerifyCodeForm email="user@example.com" />)
      await elapseCountdown()

      fireEvent.click(screen.getByTestId('verify-resend-button'))

      expect(fetchMock).toHaveBeenCalledTimes(1)
      const [url, init] = fetchMock.mock.calls[0]
      expect(url).toBe('/api/v1/auth/resend-code')
      expect(init.method).toBe('POST')
      expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
      expect(JSON.parse(init.body)).toEqual({ email: 'user@example.com' })
    })

    it('restarts the countdown after a resend that succeeded', async () => {
      vi.useFakeTimers()
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, json: async () => ({ code: '123456' }) }),
      )

      renderWithRouter(<VerifyCodeForm email="user@example.com" />)
      await elapseCountdown()

      await act(async () => {
        fireEvent.click(screen.getByTestId('verify-resend-button'))
      })

      expect(screen.getByTestId('verify-resend-countdown')).toHaveTextContent('01:00')
      expect(screen.getByTestId('verify-resend-button')).toBeDisabled()
    })

    // 404 is the LIVE behaviour, not a hypothetical: the route is specified but not deployed
    // (verified 2026-07-17). A swallowed failure leaves the user waiting for a code that was
    // never issued and blaming the mail — the worst outcome available, because it looks like
    // success. This pins that the failure reaches the screen.
    it('shows an error when the resend request fails', async () => {
      vi.useFakeTimers()
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: false,
          status: 404,
          json: async () => ({ detail: 'Not Found' }),
        }),
      )

      renderWithRouter(<VerifyCodeForm email="user@example.com" />)
      await elapseCountdown()

      await act(async () => {
        fireEvent.click(screen.getByTestId('verify-resend-button'))
      })

      expect(screen.getByTestId('verify-form-error')).toHaveTextContent(
        'Не удалось отправить код повторно. Попробуйте ещё раз позже.',
      )
    })

    // A failed resend must NOT restart the wait: the server accepted nothing, so locking the
    // user out for another minute would punish them for our 404.
    it('leaves the resend available after a resend that failed', async () => {
      vi.useFakeTimers()
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) }),
      )

      renderWithRouter(<VerifyCodeForm email="user@example.com" />)
      await elapseCountdown()

      await act(async () => {
        fireEvent.click(screen.getByTestId('verify-resend-button'))
      })

      expect(screen.getByTestId('verify-resend-countdown')).toHaveTextContent('00:00')
      expect(screen.getByTestId('verify-resend-button')).toBeEnabled()
    })
  })
})
