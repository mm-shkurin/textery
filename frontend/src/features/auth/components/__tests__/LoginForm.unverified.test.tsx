import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import * as api from '../../api/loginApi'

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

  // Spec 5.3: a distinct message directing the user toward verification. Two guards:
  //  - Queried by role="alert", NOT by testid: for a sighted user "the message reached them" means
  //    the text is on screen, but for a screen-reader user it means the live region ANNOUNCED it.
  //    LoginForm.tsx:167 carries role="alert" deliberately ("a screen reader must be told"); a
  //    refactor that drops or renames it would leave the text present-but-unannounced and stay
  //    green under a testid query. findByRole makes that regression fail. The testid is still the
  //    Selenium contract, so we assert the SAME element carries it.
  //  - Exact toBe(UNVERIFIED_MESSAGE): the premortem-named guard. A generic-fallback regression
  //    that routed UNVERIFIED back through GENERIC_LOGIN_FAILURE_MESSAGE would render "Не удалось
  //    войти" here — telling the user the one thing that is not true, that their password was
  //    wrong — and this exact equality fails the moment that happens. (An explicit
  //    not.toBe(GENERIC) line was dropped as tautological: since the two constants differ, it can
  //    only fail once the positive toBe has already failed — the positive IS the guard.)
  it('announces the distinct unverified message via role=alert on an UNVERIFIED rejection', async () => {
    vi.mocked(api.login).mockRejectedValue(UNVERIFIED_ERROR)

    renderAndSubmit()

    const error = await screen.findByRole('alert')
    expect(error).toHaveAttribute('data-testid', 'login-form-error')
    expect(error.textContent).toBe(UNVERIFIED_MESSAGE)
  })
})
