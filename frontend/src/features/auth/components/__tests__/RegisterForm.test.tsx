import { describe, expect, it } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { RegisterForm } from '../RegisterForm'

describe('RegisterForm', () => {
  it('displays email, password, confirm password fields and submit button', () => {
    renderWithRouter(<RegisterForm />)

    expect(screen.getByTestId('register-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('register-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('register-confirm-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByRole('button', { name: 'Зарегистрироваться' })).toBeInTheDocument()
  })

  it('disables the submit button immediately after it is clicked', () => {
    renderWithRouter(<RegisterForm />)
    const submitButton = screen.getByTestId('register-submit-button')
    expect(submitButton).not.toBeDisabled()

    fireEvent.click(submitButton)

    expect(submitButton).toBeDisabled()
  })

  it('shows a loading indicator while submitting and not before', () => {
    renderWithRouter(<RegisterForm />)
    const submitButton = screen.getByTestId('register-submit-button')
    expect(screen.queryByTestId('register-loading-indicator')).not.toBeInTheDocument()

    fireEvent.click(submitButton)

    expect(screen.getByTestId('register-loading-indicator')).toBeInTheDocument()
  })
})
