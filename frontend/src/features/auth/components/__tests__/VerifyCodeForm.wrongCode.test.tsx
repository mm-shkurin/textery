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

// RED (Scenario 5.5): un-skip in green-frontend. Fails today because applyVerifyError has no
// errorCode-keyed wrong-code branch — an INVALID_OR_EXPIRED_CODE with no server message falls
// through to GENERIC_VERIFY_FAILURE_MESSAGE ('Не удалось подтвердить код') instead of the distinct
// wrong-code copy. Confirmed: expected wrong-code text, received the generic fallback.
describe.skip('VerifyCodeForm wrong code', () => {
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
})
