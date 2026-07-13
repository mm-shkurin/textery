import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { LoginForm } from '../LoginForm'

describe('LoginForm', () => {
  it('displays email, password fields and submit button', () => {
    render(<LoginForm />)

    expect(screen.getByTestId('login-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('login-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('login-submit-button')).toHaveTextContent('Войти')
  })

  it('prevents native form navigation on submit (Enter-key or button)', () => {
    render(<LoginForm />)
    const form = screen.getByTestId('login-submit-button').closest('form')
    expect(form).not.toBeNull()

    const submitEvent = fireEvent.submit(form as HTMLFormElement)

    expect(submitEvent).toBe(false)
  })
})
