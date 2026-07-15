import { describe, expect, it } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { RegisterForm } from '../RegisterForm'
import { PASSWORD_POLICY_HINT } from '../../utils/passwordPolicy'

const MISMATCH_MESSAGE = 'Пароли не совпадают'

describe('RegisterForm confirm password validation', () => {
  it('shows an inline validation message when confirm password does not match password on blur', () => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')
    const confirmInput = screen.getByTestId('register-confirm-password-input')
    expect(screen.queryByTestId('register-confirm-error')).not.toBeInTheDocument()

    fireEvent.change(passwordInput, { target: { value: 'Str0ng!Pass' } })
    fireEvent.change(confirmInput, { target: { value: 'Different1!' } })
    fireEvent.blur(confirmInput)

    expect(screen.getByTestId('register-confirm-error')).toHaveTextContent(MISMATCH_MESSAGE, { exact: true })
  })

  it('shows no inline validation message when confirm password matches password on blur', () => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')
    const confirmInput = screen.getByTestId('register-confirm-password-input')

    fireEvent.change(passwordInput, { target: { value: 'Str0ng!Pass' } })
    fireEvent.change(confirmInput, { target: { value: 'Str0ng!Pass' } })
    fireEvent.blur(confirmInput)

    expect(screen.queryByTestId('register-confirm-error')).not.toBeInTheDocument()
  })

  it('shows no inline validation message when confirm password is blurred while empty', () => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')
    const confirmInput = screen.getByTestId('register-confirm-password-input')

    fireEvent.change(passwordInput, { target: { value: 'Str0ng!Pass' } })
    fireEvent.blur(confirmInput)

    expect(screen.queryByTestId('register-confirm-error')).not.toBeInTheDocument()
  })

  it('shows no inline validation message when both password and confirm password are empty on blur', () => {
    renderWithRouter(<RegisterForm />)
    const confirmInput = screen.getByTestId('register-confirm-password-input')

    fireEvent.blur(confirmInput)

    expect(screen.queryByTestId('register-confirm-error')).not.toBeInTheDocument()
  })

  it('clears the mismatch error once the confirm password is corrected to match, on the same instance', () => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')
    const confirmInput = screen.getByTestId('register-confirm-password-input')

    fireEvent.change(passwordInput, { target: { value: 'Str0ng!Pass' } })
    fireEvent.change(confirmInput, { target: { value: 'Different1!' } })
    fireEvent.blur(confirmInput)
    expect(screen.getByTestId('register-confirm-error')).toHaveTextContent(MISMATCH_MESSAGE, { exact: true })

    fireEvent.change(confirmInput, { target: { value: 'Str0ng!Pass' } })
    fireEvent.blur(confirmInput)

    expect(screen.queryByTestId('register-confirm-error')).not.toBeInTheDocument()
  })

  it('shows both the password policy error and the confirm mismatch error when password is invalid and confirm does not match', () => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')
    const confirmInput = screen.getByTestId('register-confirm-password-input')

    fireEvent.change(passwordInput, { target: { value: 'weak' } })
    fireEvent.blur(passwordInput)
    fireEvent.change(confirmInput, { target: { value: 'Different1!' } })
    fireEvent.blur(confirmInput)

    expect(screen.getByTestId('register-password-error')).toHaveTextContent(PASSWORD_POLICY_HINT, { exact: true })
    expect(screen.getByTestId('register-confirm-error')).toHaveTextContent(MISMATCH_MESSAGE, { exact: true })
  })
})
