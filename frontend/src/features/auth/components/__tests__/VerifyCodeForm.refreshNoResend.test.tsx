import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { VerifyCodeForm } from '../VerifyCodeForm'
import * as authApi from '../../api/authApi'
import { RESEND_COUNTDOWN_SECONDS } from '../../hooks/useResendCountdown'

// Scenario 5.7 — refreshing / re-mounting the verification-code screen must NOT auto-issue a
// resend. A resend is a deliberate user action (the cooldown button), never a side effect of the
// screen appearing.
//
// BORN-GREEN regression guard, NOT a true RED. VerifyCodeForm has no mount effect and no
// router-state/query-param resend path — `resendCode` is reachable ONLY from the button's onClick
// (gated by the countdown). So a fresh mount already fires zero resends. This file pins that
// invariant so a future "auto-resend on mount" effect (or a mount-time restart) goes RED, and the
// last test proves the pin is not vacuous: resend DOES fire on the explicit action, exactly once.
//
// Mock the api module (mirrors VerifyCodeForm.wrongCode.test.tsx's verifyApi mock) so the assertion
// is on `resendCode` itself, not an incidental fetch — the display seam is the api boundary.
vi.mock('../../api/authApi', async (importOriginal) => {
  const actual = await importOriginal<typeof authApi>()
  return { ...actual, resendCode: vi.fn() }
})

describe('VerifyCodeForm refresh does not resend', () => {
  afterEach(() => {
    vi.mocked(authApi.resendCode).mockReset()
    vi.useRealTimers()
  })

  it('does not call resendCode when the screen first mounts', () => {
    vi.mocked(authApi.resendCode).mockResolvedValue({ code: '123456' })

    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    // The resend is a user action, not a mount side effect. Nothing has been clicked, so the
    // endpoint must be untouched and the button must sit in its initial cooldown (disabled),
    // not fire and not be immediately available.
    expect(authApi.resendCode).not.toHaveBeenCalled()
    expect(screen.getByTestId('verify-resend-button')).toBeDisabled()
  })

  it('does not call resendCode when the screen is re-mounted, as a page refresh would', () => {
    vi.mocked(authApi.resendCode).mockResolvedValue({ code: '123456' })

    // A real browser refresh tears the component down and mounts it fresh. Simulate exactly that:
    // unmount, then render again. Fresh state (countdown back to full) must still issue no resend.
    const { unmount } = renderWithRouter(<VerifyCodeForm email="user@example.com" />)
    unmount()
    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    expect(authApi.resendCode).not.toHaveBeenCalled()
    expect(screen.getByTestId('verify-resend-countdown')).toHaveTextContent('01:00')
  })

  it('calls resendCode only on the explicit button click after the cooldown, exactly once', async () => {
    vi.useFakeTimers()
    vi.mocked(authApi.resendCode).mockResolvedValue({ code: '123456' })

    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    // Still nothing while the cooldown runs — the button is disabled and the handler refuses.
    expect(authApi.resendCode).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(RESEND_COUNTDOWN_SECONDS * 1000)
    })

    await act(async () => {
      fireEvent.click(screen.getByTestId('verify-resend-button'))
    })

    // The pin is not vacuous: resend fires on the deliberate action, and exactly once per click —
    // the mount/refresh assertions above mean "zero resends", not "resend is unreachable".
    expect(authApi.resendCode).toHaveBeenCalledTimes(1)
    expect(authApi.resendCode).toHaveBeenCalledWith('user@example.com')
  })
})
