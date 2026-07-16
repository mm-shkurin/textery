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
const SESSION = { accessToken: 'access-token', refreshToken: 'refresh-token' }
const INVALID_CREDENTIALS_ERROR = {
  errorCode: 'INVALID_CREDENTIALS',
  message: 'Неверный email или пароль',
}

function renderAndFill() {
  renderWithRouter(<LoginForm />)
  fireEvent.change(screen.getByTestId('login-email-input'), { target: { value: EMAIL } })
  fireEvent.change(screen.getByTestId('login-password-input'), { target: { value: PASSWORD } })
  return { submitButton: screen.getByTestId('login-submit-button') }
}

describe('LoginForm invalid-credentials error', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
  })

  it('calls loginApi.login with the entered email and password on submit', async () => {
    vi.mocked(api.login).mockResolvedValue(SESSION)
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    await waitFor(() => expect(api.login).toHaveBeenCalledTimes(1))
    expect(api.login).toHaveBeenCalledWith(EMAIL, PASSWORD)
  })

  // Covers both obligations spec 5.2 places on the form: it displays the generic message,
  // and it does not indicate whether the email exists. Genericness of the text itself is a
  // backend guarantee (API test 5.2: identical error_code/message for unknown-email and
  // wrong-password), so the form's entire share of both lines is verbatim pass-through —
  // exact equality proves it appends no email and no existence hint of its own.
  it('displays the server error message verbatim, adding no email-existence detail', async () => {
    vi.mocked(api.login).mockRejectedValue(INVALID_CREDENTIALS_ERROR)
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    const error = await screen.findByTestId('login-form-error')
    expect(error.textContent).toBe(INVALID_CREDENTIALS_ERROR.message)
  })

  it('displays exactly one error element, not a per-field error, on invalid credentials', async () => {
    vi.mocked(api.login).mockRejectedValue(INVALID_CREDENTIALS_ERROR)
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    await screen.findByTestId('login-form-error')
    expect(screen.queryAllByTestId('login-form-error')).toHaveLength(1)
  })

  it('does not display an error while the login call is still pending', async () => {
    let resolveLogin: (value: typeof SESSION) => void = () => {}
    vi.mocked(api.login).mockReturnValue(
      new Promise((resolve) => {
        resolveLogin = resolve
      }),
    )
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    await waitFor(() => expect(api.login).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()

    resolveLogin(SESSION)
  })

  it('does not display an error after a successful login', async () => {
    vi.mocked(api.login).mockResolvedValue(SESSION)
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    // Sync on the call settling, not on the call being made: login is invoked
    // synchronously, so waiting on the mock's call count would assert the pending
    // state and re-guard the test above instead of the post-success state.
    await waitFor(() => expect(submitButton).not.toBeDisabled())
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })

  it('clears a previous invalid-credentials error after a corrected resubmission succeeds', async () => {
    vi.mocked(api.login).mockRejectedValueOnce(INVALID_CREDENTIALS_ERROR)
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)
    await screen.findByTestId('login-form-error')

    vi.mocked(api.login).mockResolvedValueOnce(SESSION)
    await waitFor(() => expect(submitButton).not.toBeDisabled())
    fireEvent.click(submitButton)

    await waitFor(() => expect(api.login).toHaveBeenCalledTimes(2))
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })
})
