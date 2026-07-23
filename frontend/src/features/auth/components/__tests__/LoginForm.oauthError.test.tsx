import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LoginForm } from '../LoginForm'

// Scenario 4.1 (display half) — when the OAuth callback routes back to /login on a provider
// error, it carries a provider-aware message in `location.state.oauthError`. The login screen must
// surface it as a DISTINCT banner: its own element with `data-testid="login-oauth-error"` and
// `role="alert"`, SEPARATE from the field-validation error (`login-form-error`) so the failure
// reads as "sign-in through the provider failed", not "your password was wrong". Mirrors the
// existing distinct-element pattern for the network error (LoginForm.tsx:176-184).
//
// A pure render test (no submit, no api call) — the message comes from router state, so it needs
// only a MemoryRouter entry that carries it. loginApi is untouched: nothing here calls login().

const VK_ERROR_MESSAGE = 'Не удалось войти через VK ID. Попробуйте снова.'

function renderWithOAuthError() {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/login', state: { oauthError: VK_ERROR_MESSAGE } }]}>
      <LoginForm />
    </MemoryRouter>,
  )
}

describe('LoginForm OAuth provider-error banner', () => {
  it('renders the provider-aware oauthError from router state as a distinct alert banner', () => {
    renderWithOAuthError()

    const banner = screen.getByTestId('login-oauth-error')
    // Exact match, not substring: the banner renders the provider-aware copy verbatim, nothing more.
    expect(banner.textContent).toBe(VK_ERROR_MESSAGE)
    expect(banner).toHaveAttribute('role', 'alert')
  })

  // The banner is its OWN element, not the field-validation error — a provider failure must never
  // masquerade as a wrong-password/validation message (spec 02_UI_Tests.md:78, Gherkin last line).
  it('shows the oauthError as a separate element from the field-validation error', () => {
    renderWithOAuthError()

    expect(screen.getByTestId('login-oauth-error')).toBeInTheDocument()
    expect(screen.queryByTestId('login-form-error')).not.toBeInTheDocument()
  })

  // Negative: a plain /login visit with NO router state renders NO banner — the banner is gated on
  // a usable oauthError, so an ordinary login never shows a stray provider-failure box.
  it('renders no oauth-error banner when there is no navigation state', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginForm />
      </MemoryRouter>,
    )

    expect(screen.queryByTestId('login-oauth-error')).not.toBeInTheDocument()
  })
})
