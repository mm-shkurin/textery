import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { VerifyCodeForm } from '../VerifyCodeForm'
import * as verifyApi from '../../api/verifyApi'
import { GENERIC_VERIFY_FAILURE_MESSAGE } from '../../utils/authMessages'

// Scenario 5.5 — a rejected code must produce a DISTINCT wrong-code message, not the generic
// "could not confirm" fallback. Honors the display seam (5.2 thesis, round-8 premortem): the api
// hands the form the wire code with NO display copy (`message: ''`), and the FORM owns the copy it
// shows — keyed on errorCode, exactly as login's loginErrorMessage maps UNVERIFIED to its own text.
// INVALID_OR_EXPIRED_CODE deliberately collapses wrong/expired/no-account/no-code into one code
// (the enumeration oracle this story exists to avoid), so the client shows ONE wrong-code message
// and never tries to tell those causes apart.

// The wrong-code copy the form must own. Distinct from GENERIC_VERIFY_FAILURE_MESSAGE
// ('Не удалось подтвердить код') — inlined as a literal here, as the other verify tests inline
// their expected strings; green defines the shared constant with this exact text.
const WRONG_CODE_MESSAGE = 'Неверный или устаревший код. Проверьте его и попробуйте снова.'

vi.mock('../../api/verifyApi', async (importOriginal) => {
  const actual = await importOriginal<typeof verifyApi>()
  return { ...actual, verify: vi.fn() }
})

describe('VerifyCodeForm wrong code', () => {
  it('shows a distinct wrong-code message when the server rejects the submitted code', async () => {
    vi.mocked(verifyApi.verify).mockRejectedValue({
      errorCode: 'INVALID_OR_EXPIRED_CODE',
      message: '',
    })
    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    fireEvent.click(screen.getByTestId('verify-confirm-button'))

    // Pin the scenario's defining property: the wrong-code copy is genuinely DISTINCT from the
    // generic fallback. Without this, green could collapse the two strings and the exact-match
    // below would still pass on the generic text.
    expect(WRONG_CODE_MESSAGE).not.toBe(GENERIC_VERIFY_FAILURE_MESSAGE)

    const error = await screen.findByTestId('verify-form-error')
    expect(error.textContent).toBe(WRONG_CODE_MESSAGE)
  })

  // Premortem guard (a11y): for a sighted user "the message reached them" means the text is on
  // screen, but for a screen-reader user it means the live region ANNOUNCED it. VerifyCodeForm's
  // error carries role="alert" deliberately; a refactor dropping or renaming it would leave the
  // text present-but-unannounced and stay green under the testid query above. Query by role and
  // assert the SAME element carries the Selenium testid + the exact copy — mirrors
  // LoginForm.unverified.test.tsx:59-61.
  it('announces the wrong-code message via role=alert on the same element that carries the testid', async () => {
    vi.mocked(verifyApi.verify).mockRejectedValue({
      errorCode: 'INVALID_OR_EXPIRED_CODE',
      message: '',
    })
    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    fireEvent.click(screen.getByTestId('verify-confirm-button'))

    const error = await screen.findByRole('alert')
    expect(error).toHaveAttribute('data-testid', 'verify-form-error')
    expect(error.textContent).toBe(WRONG_CODE_MESSAGE)
  })

  // Premortem guard (INVALID_CODE): the malformed-code 400 is a DISTINCT backend code, but it gives
  // the user the same action — re-check the code — so the client shows the SAME wrong-code message
  // rather than surfacing a cause distinction they cannot act on (consistent with the enumeration
  // oracle). Pins that decision so INVALID_CODE cannot silently drift to the generic fallback.
  it('shows the same wrong-code message for a malformed-code INVALID_CODE rejection', async () => {
    vi.mocked(verifyApi.verify).mockRejectedValue({
      errorCode: 'INVALID_CODE',
      message: '',
    })
    renderWithRouter(<VerifyCodeForm email="user@example.com" />)

    fireEvent.click(screen.getByTestId('verify-confirm-button'))

    const error = await screen.findByTestId('verify-form-error')
    expect(error.textContent).toBe(WRONG_CODE_MESSAGE)
  })
})
