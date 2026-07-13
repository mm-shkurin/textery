import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RegisterForm } from '../RegisterForm'

describe('RegisterForm', () => {
  it('displays email, password, confirm password fields and submit button', () => {
    render(<RegisterForm />)

    expect(screen.getByTestId('register-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('register-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('register-confirm-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByRole('button', { name: 'Зарегистрироваться' })).toBeInTheDocument()
  })
})
