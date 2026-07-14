import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LoginForm } from '../LoginForm'

describe('LoginForm', () => {
  it('displays email, password fields and submit button', () => {
    render(
      <MemoryRouter>
        <LoginForm />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('login-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('login-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('login-submit-button')).toHaveTextContent('Войти')
  })

  it('associates labels with the email and password inputs', () => {
    render(
      <MemoryRouter>
        <LoginForm />
      </MemoryRouter>,
    )

    expect(screen.getByLabelText('Email')).toBe(screen.getByTestId('login-email-input'))
    expect(screen.getByLabelText('Пароль')).toBe(screen.getByTestId('login-password-input'))
  })

  it('prevents native form navigation on submit (Enter-key or button)', () => {
    render(
      <MemoryRouter>
        <LoginForm />
      </MemoryRouter>,
    )
    const form = screen.getByTestId('login-submit-button').closest('form')
    expect(form).not.toBeNull()

    const submitEvent = fireEvent.submit(form as HTMLFormElement)

    expect(submitEvent).toBe(false)
  })

  // TDD Red Phase - Scenario 2.1: show-password toggle not implemented in LoginForm.tsx
  it.skip('does not submit the form when the show-password toggle is clicked', () => {
    render(
      <MemoryRouter>
        <LoginForm />
      </MemoryRouter>,
    )
    const form = screen.getByTestId('login-submit-button').closest('form') as HTMLFormElement
    const submitHandler = vi.fn((event: Event) => event.preventDefault())
    form.addEventListener('submit', submitHandler)

    fireEvent.click(screen.getByTestId('login-password-toggle'))

    expect(submitHandler).not.toHaveBeenCalled()
  })

  // TDD Red Phase - Scenario 2.1: show-password toggle not implemented in LoginForm.tsx
  it.skip('reverts the password field back to masked when the toggle is clicked twice', () => {
    render(
      <MemoryRouter>
        <LoginForm />
      </MemoryRouter>,
    )
    const passwordInput = screen.getByTestId('login-password-input')
    const toggle = screen.getByTestId('login-password-toggle')

    fireEvent.click(toggle)
    expect(passwordInput).toHaveAttribute('type', 'text')

    fireEvent.click(toggle)
    expect(passwordInput).toHaveAttribute('type', 'password')
  })
})
