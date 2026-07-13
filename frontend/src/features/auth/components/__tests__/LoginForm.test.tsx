import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LoginForm } from '../LoginForm'

describe('LoginForm', () => {
  it('displays email, password fields and submit button', () => {
    render(<LoginForm />)

    expect(screen.getByTestId('login-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('login-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('login-submit-button')).toHaveTextContent('Войти')
  })
})
