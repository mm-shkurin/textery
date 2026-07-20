import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import * as api from '../../api/loginApi'
import { GENERIC_LOGIN_FAILURE_MESSAGE } from '../../utils/authMessages'

vi.mock('../../api/loginApi', () => ({
  login: vi.fn(),
}))

const EMAIL = 'user@example.com'
const PASSWORD = 'Str0ng!Pass'

// The distinct UNVERIFIED copy the form must render — a password that was RIGHT plus an account
// that must go confirm its code. Sourced verbatim from LoginForm's UNVERIFIED_MESSAGE constant.
// If the form ever re-worded this, that is a product decision that should break this test loudly,
// not slide through a `contains` match.
const UNVERIFIED_MESSAGE = 'Аккаунт не подтверждён. Введите код подтверждения из письма.'

// The backend answers an unverified account with 403 { error_code: "UNVERIFIED", message }
// (confirmed live 2026-07-16). The message field is deliberately given a DIFFERENT string than
// what the form renders, so the test proves the form branches on the CODE and substitutes its own
// copy — not that it passes the server message through.
const UNVERIFIED_ERROR = {
  errorCode: 'UNVERIFIED',
  message: 'not verified',
}

function renderAndSubmit() {
  renderWithRouter(<LoginForm />)
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })
  fireEvent.click(screen.getByTestId('login-submit-button'))
}

describe('LoginForm unverified-account error', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
  })

  // Spec 5.3: a distinct message directing the user toward verification. Exact equality proves the
  // form renders its OWN distinct copy, and the negative assertion is the guard the premortem for
  // this scenario named: a generic-fallback regression that routed UNVERIFIED back through
  // GENERIC_LOGIN_FAILURE_MESSAGE would silently swallow the distinction and tell the user the one
  // thing that is not true — their password was fine. That regression must fail here.
  it('renders the distinct unverified message, not the generic login-failure copy, on an UNVERIFIED rejection', async () => {
    vi.mocked(api.login).mockRejectedValue(UNVERIFIED_ERROR)

    renderAndSubmit()

    const error = await screen.findByTestId('login-form-error')
    expect(error.textContent).toBe(UNVERIFIED_MESSAGE)
    expect(error.textContent).not.toBe(GENERIC_LOGIN_FAILURE_MESSAGE)
  })
})
