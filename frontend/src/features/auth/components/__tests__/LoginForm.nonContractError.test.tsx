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
// that never carried a contract body — a transport failure, an unrecognised error code —
// is outside that guarantee, so the form must not render its text. This is spec 5.2's own
// non-disclosure clause: which distinct message 5.3/5.6 show is their scope, but "an
// internal error string never becomes user-facing text on the login screen" is 5.2's.
describe('LoginForm non-contract rejections', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
  })

  it('displays no error text when login rejects with a bodyless transport failure', async () => {
    vi.mocked(api.login).mockRejectedValue(new TypeError('Failed to fetch'))
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })

  it('displays no error text when login rejects with an unrecognised error code', async () => {
    vi.mocked(api.login).mockRejectedValue({
      errorCode: 'INTERNAL_SERVER_ERROR',
      message: 'NullPointerException at AuthService.line42',
    })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })

  it('displays no error text when a contract-shaped rejection carries no message', async () => {
    vi.mocked(api.login).mockRejectedValue({ errorCode: 'INVALID_CREDENTIALS' })
    const { submitButton } = renderAndSubmit()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })
})
