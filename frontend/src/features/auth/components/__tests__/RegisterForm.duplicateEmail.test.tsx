import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { RegisterForm } from '../RegisterForm'
import * as api from '../../api/registerApi'
import type { RegisterResult } from '../../api/registerApi'

vi.mock('../../api/registerApi', () => ({
  register: vi.fn(),
}))

const VALID_EMAIL = 'user@example.com'
const VALID_PASSWORD = 'Str0ng!Pass'
// 'EMAIL_ALREADY_REGISTERED' is the code the backend actually sends on 409, confirmed by
// curl against the live stack. These tests previously asserted 'EMAIL_ALREADY_EXISTS' — a
// code nothing emits — and passed anyway, because the module under test is mocked here.
// Mocking the api is what let the invented contract stay green.
const DUPLICATE_EMAIL_ERROR = {
  errorCode: 'EMAIL_ALREADY_REGISTERED',
  message: 'An account with this email address already exists.',
}

// Annotated with the API's own type rather than left to inference: an inferred fixture keeps
// compiling when RegisterResult gains a field, and silently stops standing for what register
// returns. That is exactly how the `{ email }` shapes below drifted.
const REGISTER_SUCCESS: RegisterResult = {
  userId: '00000000-0000-0000-0000-000000000001',
  email: VALID_EMAIL,
  isVerified: false,
  verificationCode: '123456',
  codeExpiresAt: '2026-07-16T18:00:00+00:00',
}

function renderAndFill() {
  renderWithRouter(<RegisterForm />)
  const emailInput = screen.getByTestId('register-email-input')
  const passwordInput = screen.getByTestId('register-password-input')
  const confirmInput = screen.getByTestId('register-confirm-password-input')
  fireEvent.change(emailInput, { target: { value: VALID_EMAIL } })
  fireEvent.change(passwordInput, { target: { value: VALID_PASSWORD } })
  fireEvent.change(confirmInput, { target: { value: VALID_PASSWORD } })
  return { emailInput, submitButton: screen.getByTestId('register-submit-button') }
}

describe('RegisterForm duplicate-email error', () => {
  afterEach(() => {
    vi.mocked(api.register).mockReset()
  })

  it('calls registerApi.register with the entered email, password and confirmation on submit', async () => {
    vi.mocked(api.register).mockResolvedValue(REGISTER_SUCCESS)
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    await waitFor(() => expect(api.register).toHaveBeenCalledTimes(1))
    expect(api.register).toHaveBeenCalledWith(VALID_EMAIL, VALID_PASSWORD, VALID_PASSWORD)
  })

  it('displays the duplicate-email error near the email field when register rejects with EMAIL_ALREADY_REGISTERED', async () => {
    vi.mocked(api.register).mockRejectedValue(DUPLICATE_EMAIL_ERROR)
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    const error = await screen.findByTestId('register-email-error')
    expect(error).toHaveTextContent(DUPLICATE_EMAIL_ERROR.message)
  })

  it('does not display an email error while the register call is still pending', async () => {
    let resolveRegister: (value: RegisterResult) => void = () => {}
    vi.mocked(api.register).mockReturnValue(
      new Promise((resolve) => {
        resolveRegister = resolve
      }),
    )
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    await waitFor(() => expect(api.register).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId('register-email-error')).not.toBeInTheDocument()

    resolveRegister(REGISTER_SUCCESS)
  })

  it('does not display an email error after a successful registration', async () => {
    vi.mocked(api.register).mockResolvedValue(REGISTER_SUCCESS)
    const { submitButton } = renderAndFill()

    fireEvent.click(submitButton)

    await waitFor(() => expect(api.register).toHaveBeenCalledTimes(1))
    expect(screen.queryByTestId('register-email-error')).not.toBeInTheDocument()
  })

  it('clears a previous duplicate-email error after a corrected resubmission succeeds', async () => {
    vi.mocked(api.register).mockRejectedValueOnce(DUPLICATE_EMAIL_ERROR)
    const { emailInput, submitButton } = renderAndFill()

    fireEvent.click(submitButton)
    await screen.findByTestId('register-email-error')

    vi.mocked(api.register).mockResolvedValueOnce({
      ...REGISTER_SUCCESS,
      email: 'other@example.com',
    })
    fireEvent.change(emailInput, { target: { value: 'other@example.com' } })
    await waitFor(() => expect(submitButton).not.toBeDisabled())
    fireEvent.click(submitButton)

    await waitFor(() => expect(api.register).toHaveBeenCalledTimes(2))
    expect(screen.queryByTestId('register-email-error')).not.toBeInTheDocument()
  })
})
