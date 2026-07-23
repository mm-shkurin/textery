import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthErrorBanner } from '../OAuthErrorBanner'

// Scenario 4.1 follow-up — CARRIED premortem #1: the discriminating survives-the-scrub case.
//
// The sibling OAuthErrorBanner.staleBanner.test.tsx mocks useNavigate to a NO-OP, so its scrub
// never actually clears location.state — a green that reads live state instead of capturing would
// still pass there. This file leaves react-router FULLY REAL: the component's clear-once effect
// fires a genuine navigate(pathname, { replace: true, state: {} }), which really clears the history
// entry and re-renders the banner against the cleared state. Because the banner renders from the
// CAPTURED local value (lazy useState), it must STAY visible with the exact message. A live-reading
// implementation would blank here — proven against a live probe during green.
//
// No react-router mock: the point is the real scrub. MemoryRouter drives location.pathname/state.

const MESSAGE = 'Не удалось войти через VK ID. Попробуйте снова.'

function renderAt(state: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/login', state }]}>
      <OAuthErrorBanner />
    </MemoryRouter>,
  )
}

describe('OAuthErrorBanner survives the real history scrub', () => {
  it('keeps the exact message after the effect clears location.state', async () => {
    renderAt({ oauthError: MESSAGE })

    // Present on first render.
    expect(screen.getByTestId('login-oauth-error').textContent).toBe(MESSAGE)

    // The real scrub has fired and cleared location.state; the captured banner must persist.
    await waitFor(() => {
      expect(screen.getByTestId('login-oauth-error').textContent).toBe(MESSAGE)
    })
    expect(screen.getByTestId('login-oauth-error')).toHaveAttribute('role', 'alert')
  })
})
