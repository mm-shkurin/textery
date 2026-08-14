import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { VerifyCodeForm } from '../VerifyCodeForm'
import { RESEND_COUNTDOWN_SECONDS } from '../../hooks/useResendCountdown'

// THE BUG THIS PINS, end to end, because it cost a user their account:
//
// No mail is sent, so the code printed on this screen is the only one the user has. A resend
// ISSUES A NEW CODE and retires the previous one — but the screen read the code from immutable
// router state, and the client dropped the response body on the floor (it also read the wrong
// field: the route answers `verification_code`, the interface claimed `code`).
//
// So «Отправить снова» left the retired code on screen. The user typed what they were shown, the
// server refused it, the account stayed unverified — and an unverified account is answered with
// 403 UNVERIFIED at the login screen. "I registered and now I cannot sign in."
//
// Nothing caught it: the api test asserted a pass-through of a fixture in a shape the backend
// never sends, and every component test mocked the client away.
describe('VerifyCodeForm resend replaces the code on screen', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  function renderWithCode(code: string) {
    return render(
      <MemoryRouter initialEntries={[{ pathname: '/verify', state: { email: 'user@example.com', verificationCode: code } }]}>
        <VerifyCodeForm />
      </MemoryRouter>,
    )
  }

  it('shows the newly issued code, not the one it replaced', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        // The real wire shape. With `{code}` here the test would pass against the broken client.
        json: async () => ({ verification_code: '654321', code_expires_at: '2026-08-14T10:00:00+00:00' }),
      }),
    )

    renderWithCode('123456')
    expect(screen.getByTestId('verify-dev-code')).toHaveTextContent('123456')

    await act(async () => {
      vi.advanceTimersByTime(RESEND_COUNTDOWN_SECONDS * 1000)
    })
    await act(async () => {
      fireEvent.click(screen.getByTestId('verify-resend-button'))
    })

    const shown = screen.getByTestId('verify-dev-code')
    expect(shown).toHaveTextContent('654321')
    // The retired code must be GONE, not merely joined by the new one: two six-digit numbers on
    // screen and the user picks the wrong one half the time.
    expect(shown).not.toHaveTextContent('123456')
  })

  it('clears the digits the user had already typed for the retired code', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ verification_code: '654321', code_expires_at: '2026-08-14T10:00:00+00:00' }),
      }),
    )

    renderWithCode('123456')
    const boxes = screen.getAllByRole('textbox')
    fireEvent.change(boxes[0], { target: { value: '1' } })
    expect(boxes[0]).toHaveValue('1')

    await act(async () => {
      vi.advanceTimersByTime(RESEND_COUNTDOWN_SECONDS * 1000)
    })
    await act(async () => {
      fireEvent.click(screen.getByTestId('verify-resend-button'))
    })

    // Half-typed digits belong to a code that no longer works. Left in place they are a trap:
    // the user finishes typing the new code onto the tail of the old one.
    expect(screen.getAllByRole('textbox')[0]).toHaveValue('')
  })
})
