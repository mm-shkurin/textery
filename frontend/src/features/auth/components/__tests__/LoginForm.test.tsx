import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'
import * as api from '../../api/loginApi'
import type { LoginResult } from '../../api/loginApi'

vi.mock('../../api/loginApi', () => ({
  login: vi.fn(),
}))

// Annotated with the API's own type rather than left to inference. Inferred, this fixture was
// `{ accessToken, refreshToken }` and kept compiling after LoginResult gained the two expiry
// fields — the mock silently stopped standing for what login actually returns. The annotation
// is what makes the next contract change a compile error here instead of a surprise later.
const SESSION: LoginResult = {
  accessToken: 'access-token',
  refreshToken: 'refresh-token',
  accessTokenExpiresAt: '2026-07-16T18:15:00+00:00',
  refreshTokenExpiresAt: '2026-07-23T18:00:00+00:00',
}

// Hands back the resolve handle so a test can hold the login call in flight and assert
// the in-flight window deliberately, rather than racing an already-settled promise.
function mockPendingLogin() {
  let resolveLogin: (value: typeof SESSION) => void = () => {}
  vi.mocked(api.login).mockReturnValue(
    new Promise((resolve) => {
      resolveLogin = resolve
    }),
  )
  return () => resolveLogin(SESSION)
}

describe('LoginForm', () => {
  afterEach(() => {
    vi.mocked(api.login).mockReset()
  })

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

  it('disables the submit button while the login call is in flight and re-enables it once it settles', async () => {
    const finishLogin = mockPendingLogin()
    renderWithRouter(<LoginForm />)
    const submitButton = screen.getByTestId('login-submit-button')
    expect(submitButton).not.toBeDisabled()

    fireEvent.click(submitButton)

    // Still disabled while login has genuinely not settled — binds the guard to the
    // real in-flight boundary rather than to whatever the promise happens to do.
    expect(submitButton).toBeDisabled()

    finishLogin()
    await waitFor(() => expect(submitButton).not.toBeDisabled())
  })

  it('shows a visible loading indicator while the login call is in flight and removes it once settled', async () => {
    const finishLogin = mockPendingLogin()
    renderWithRouter(<LoginForm />)
    const submitButton = screen.getByTestId('login-submit-button')

    expect(screen.queryByTestId('login-loading-indicator')).not.toBeInTheDocument()

    fireEvent.click(submitButton)

    const indicator = screen.getByTestId('login-loading-indicator')
    expect(indicator).toHaveClass('auth-loading-indicator')
    expect(indicator).toHaveAttribute('role', 'status')
    expect(indicator).toHaveAttribute('aria-live', 'polite')

    finishLogin()
    await waitFor(() => expect(screen.queryByTestId('login-loading-indicator')).not.toBeInTheDocument())
  })

  // A second submit reaching the server would double-count failed attempts and trip
  // Scenario 5.4's lockout at half its intended threshold. The submit event, not a
  // second click, is what the reentrancy guard has to stop: the button's disabled
  // attribute already swallows the second click, so a click-based test would pass
  // whether or not the guard exists — but Enter-key submits bypass the button entirely.
  it('sends only one login request when the form is submitted again while a call is in flight', async () => {
    const finishLogin = mockPendingLogin()
    renderWithRouter(<LoginForm />)
    const form = screen.getByTestId('login-submit-button').closest('form') as HTMLFormElement

    fireEvent.submit(form)
    fireEvent.submit(form)

    expect(api.login).toHaveBeenCalledTimes(1)

    finishLogin()
    await waitFor(() => expect(screen.getByTestId('login-submit-button')).not.toBeDisabled())
  })
})
