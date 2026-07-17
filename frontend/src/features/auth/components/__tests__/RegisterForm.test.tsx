import { describe, expect, it } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { RegisterForm } from '../RegisterForm'

describe('RegisterForm', () => {
  it('displays email, password, confirm password fields and submit button', () => {
    renderWithRouter(<RegisterForm />)

    expect(screen.getByTestId('register-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('register-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('register-confirm-password-input')).toHaveAttribute(
      'type',
      'password',
    )
    expect(screen.getByRole('button', { name: 'Зарегистрироваться' })).toBeInTheDocument()
  })

  it('disables the submit button immediately after it is clicked', () => {
    renderWithRouter(<RegisterForm />)
    const submitButton = screen.getByTestId('register-submit-button')
    expect(submitButton).not.toBeDisabled()

    fireEvent.click(submitButton)

    expect(submitButton).toBeDisabled()
  })

  it('shows a visible loading indicator while submitting and removes it once settled', async () => {
    renderWithRouter(<RegisterForm />)
    const submitButton = screen.getByTestId('register-submit-button')
    expect(screen.queryByTestId('register-loading-indicator')).not.toBeInTheDocument()

    fireEvent.click(submitButton)

    const indicator = screen.getByTestId('register-loading-indicator')
    expect(indicator).toHaveClass('auth-loading-indicator')
    expect(indicator).toHaveAttribute('role', 'status')
    expect(indicator).toHaveAttribute('aria-live', 'polite')

    await waitFor(() =>
      expect(screen.queryByTestId('register-loading-indicator')).not.toBeInTheDocument(),
    )
  })

  it('shows an inline validation message when the password does not meet the policy on blur', () => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')
    expect(screen.queryByTestId('register-password-error')).not.toBeInTheDocument()

    fireEvent.change(passwordInput, { target: { value: 'weak' } })
    fireEvent.blur(passwordInput)

    expect(screen.getByTestId('register-password-error')).toHaveTextContent(
      'Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол',
    )
  })

  it('does not render the static hint alongside the error (no duplicated message on screen)', () => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')
    const hintText = 'Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол'
    expect(screen.getAllByText(hintText)).toHaveLength(1)

    fireEvent.change(passwordInput, { target: { value: 'weak' } })
    fireEvent.blur(passwordInput)

    expect(screen.getByTestId('register-password-error')).toBeInTheDocument()
    expect(screen.getAllByText(hintText)).toHaveLength(1)
  })

  it.each([
    ['missing a digit', 'NoDigitPass!'],
    ['missing an uppercase letter', 'nouppercase1!'],
    ['missing a lowercase letter', 'NOLOWERCASE1!'],
    ['missing a special character', 'NoSpecial123'],
    ['using only whitespace where a special character is required', 'Password1 '],
    ['too short (7 chars)', 'Sh0rt!!'],
  ])('shows the inline validation message when the password is %s', (_label, value) => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')

    fireEvent.change(passwordInput, { target: { value } })
    fireEvent.blur(passwordInput)

    expect(screen.getByTestId('register-password-error')).toBeInTheDocument()
  })

  it.each([
    ['a compliant password', 'Str0ng!Pass'],
    ['a second compliant password using a different special character', 'Valid#Pass9'],
    ['a compliant password exactly at the 8-character minimum', 'Ab1!Ab1!'],
  ])('shows no inline validation message for %s', (_label, value) => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')

    fireEvent.change(passwordInput, { target: { value } })
    fireEvent.blur(passwordInput)

    expect(screen.queryByTestId('register-password-error')).not.toBeInTheDocument()
  })

  it('clears the error and restores the hint once the password is corrected to a compliant value', () => {
    renderWithRouter(<RegisterForm />)
    const passwordInput = screen.getByTestId('register-password-input')

    fireEvent.change(passwordInput, { target: { value: 'weak' } })
    fireEvent.blur(passwordInput)
    expect(screen.getByTestId('register-password-error')).toBeInTheDocument()

    fireEvent.change(passwordInput, { target: { value: 'Str0ng!Pass' } })
    fireEvent.blur(passwordInput)

    expect(screen.queryByTestId('register-password-error')).not.toBeInTheDocument()
    expect(
      screen.getAllByText(
        'Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол',
      ),
    ).toHaveLength(1)
  })
})
