import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'

describe('LoginForm', () => {
  it('displays email, password fields and submit button', () => {
    renderWithRouter(<LoginForm />)

    expect(screen.getByTestId('login-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('login-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('login-submit-button')).toHaveTextContent('Войти')
  })

  it('associates labels with the email and password inputs', () => {
    renderWithRouter(<LoginForm />)

    expect(screen.getByLabelText('Email')).toBe(screen.getByTestId('login-email-input'))
    expect(screen.getByLabelText('Пароль')).toBe(screen.getByTestId('login-password-input'))
  })

  it('prevents native form navigation on submit (Enter-key or button)', () => {
    renderWithRouter(<LoginForm />)
    const form = screen.getByTestId('login-submit-button').closest('form')
    expect(form).not.toBeNull()

    const submitEvent = fireEvent.submit(form as HTMLFormElement)

    expect(submitEvent).toBe(false)
  })

  it('does not submit the form when the show-password toggle is clicked', () => {
    renderWithRouter(<LoginForm />)
    const form = screen.getByTestId('login-submit-button').closest('form') as HTMLFormElement
    const submitHandler = vi.fn((event: Event) => event.preventDefault())
    form.addEventListener('submit', submitHandler)

    fireEvent.click(screen.getByTestId('login-password-toggle'))

    expect(submitHandler).not.toHaveBeenCalled()
  })

  it('reverts the password field back to masked when the toggle is clicked twice', () => {
    renderWithRouter(<LoginForm />)
    const passwordInput = screen.getByTestId('login-password-input')
    const toggle = screen.getByTestId('login-password-toggle')

    fireEvent.click(toggle)
    expect(passwordInput).toHaveAttribute('type', 'text')

    fireEvent.click(toggle)
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('reflects the show/hide state on the toggle button aria-pressed attribute', () => {
    renderWithRouter(<LoginForm />)
    const toggle = screen.getByTestId('login-password-toggle')

    expect(toggle).toHaveAttribute('aria-pressed', 'false')

    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-pressed', 'false')
  })

  it('disables the submit button immediately after click and re-enables it once the request settles', async () => {
    renderWithRouter(<LoginForm />)
    const submitButton = screen.getByTestId('login-submit-button')
    expect(submitButton).not.toBeDisabled()

    fireEvent.click(submitButton)

    expect(submitButton).toBeDisabled()

    await waitFor(() => expect(submitButton).not.toBeDisabled())
  })
})
