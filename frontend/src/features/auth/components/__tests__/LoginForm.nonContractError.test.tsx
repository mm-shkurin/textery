import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import * as api from '../../api/loginApi'

vi.mock('../../api/loginApi', () => ({
  login: vi.fn(),
}))

const EMAIL = 'user@example.com'
const PASSWORD = 'Str0ng!Pass'

function renderAndSubmit() {
  renderWithRouter(<LoginForm />)
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })
  const submitButton = screen.getByTestId('login-submit-button')
  fireEvent.click(submitButton)
  return { submitButton }
}

// The backend's "message is always generic and client-safe" guarantee (endpoints.md,
// hazard-scan group 7) only covers strings the backend actually produced. A rejection
// outside that guarantee must never have its text rendered — spec 5.2's non-disclosure
// clause.
//
// But NOT rendering the server's text is only half the requirement: the form must still
// say SOMETHING. Silence is an illegal terminal state. Spec 5.2's "the message does not
// indicate whether the email exists" is about the ORACLE, not the string — and the mere
// PRESENCE of the error element is an oracle. Once 5.3 lands and the backend answers
// UNVERIFIED for a registered-but-unverified account, a wrong password on a registered
// account would render a message while an unverified account renders silence: an attacker
// enumerates accounts by observing whether the div exists, never needing to read it.
//
// So every non-contract outcome resolves to a client-owned generic constant. 5.3/5.4/5.6
// will branch their own distinct messages ABOVE this fallback; INTERNAL_SERVER_ERROR is
// used here precisely because no planned scenario branches on it.
const GENERIC_LOGIN_FAILURE_MESSAGE = 'Не удалось войти'

describe('LoginForm non-contract rejections', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
  })

  // A transport failure is not an enumeration oracle — it cannot be induced per-account —
  // but it is the MOST common trigger of the silent form, so the fallback must cover it too.
  // 5.6 owns the retry-capable network state and will branch it ABOVE this fallback; until
  // then the fallback is what stands between a failed fetch and a blank form. Pinning
  // silence here would instead force green to write a TypeError-discriminating branch whose
  // only purpose is to preserve the incident this scenario exists to kill.
  it('displays the generic message, not the transport failure text, when login rejects with a bodyless transport failure', async () => {
    const transportText = 'Failed to fetch'
    vi.mocked(api.login).mockRejectedValue(new TypeError(transportText))
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    const formError = screen.getByTestId('login-form-error')
    expect(formError.textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(document.body.textContent).not.toContain(transportText)
  })

  it('displays the generic message, not the server text, when login rejects with an unrecognised error code', async () => {
    const serverText = 'NullPointerException at AuthService.line42'
    vi.mocked(api.login).mockRejectedValue({
      errorCode: 'INTERNAL_SERVER_ERROR',
      message: serverText,
    })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    const formError = screen.getByTestId('login-form-error')
    expect(formError.textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
    expect(document.body.textContent).not.toContain(serverText)
  })

  // Fixture is `message: ''`, not an absent message. An ABSENT message is unreachable:
  // `toLoginApiError` defaults it via `?? GENERIC_LOGIN_FAILURE_MESSAGE`, so loginApi can
  // never hand the form a contract error without a message — asserting that shape would be
  // a fifth vacuous guard in this scenario. An EMPTY message is reachable, because `??`
  // catches null/undefined but NOT '': a body of `{"error_code":"INVALID_CREDENTIALS",
  // "message":""}` survives toLoginApiError verbatim, applyLoginError returns '', and
  // `{formError && ...}` treats '' as falsy — silence, on the INVALID_CREDENTIALS path
  // itself. That is the enumeration oracle at its sharpest: the one outcome 5.2 already
  // renders would go silent whenever the server sends an empty string.
  it('displays the generic message when a contract-shaped rejection carries an empty message', async () => {
    vi.mocked(api.login).mockRejectedValue({ errorCode: 'INVALID_CREDENTIALS', message: '' })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.getByTestId('login-form-error').textContent).toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
  })
})
