import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthErrorBanner } from '../OAuthErrorBanner'

// Scenario 4.1 follow-up — the deferred stale-banner debt (CARRIED premortem #2 under 4.1).
//
// Today OAuthErrorBanner renders straight from the IMMUTABLE `location.state.oauthError`. Pressing
// Back onto the /login history entry — or any remount that re-reads that state — resurrects a stale
// "sign-in failed" banner even though nothing just failed. The GREEN fix (next): on first render,
// CAPTURE the message into local component state (so the banner STAYS visible this visit) and SCRUB
// the history entry via `navigate(location.pathname, { replace: true, state: {} })` in an effect, so
// a later remount reading the cleared state shows no banner.
//
// Seam mocked: react-router's useNavigate (the scrub side effect). useLocation and MemoryRouter are
// left REAL so location.pathname / location.state come from the mounted entry — mirrors the sibling
// OAuthCallback tests' mock of react-router-dom.

const MESSAGE = 'Не удалось войти через VK ID. Попробуйте снова.'

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

function renderAt(state: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/login', state }]}>
      <OAuthErrorBanner />
    </MemoryRouter>,
  )
}

afterEach(() => {
  navigate.mockReset()
})

// RED — today the component has no useNavigate and no effect, so it never scrubs the history entry.
//
// PREDICTED FAILURE (assertion 1) — trips on the toHaveBeenCalledWith line first:
//   AssertionError: expected "vi.fn()" to be called with arguments: [ '/login', { replace: true,
//   state: {} } ]  /  Number of calls: 0
// Un-skip once green captures-locally + scrubs the history entry.
describe('OAuthErrorBanner history-state scrub', () => {
  it('scrubs oauthError from the history entry after first render', () => {
    renderAt({ oauthError: MESSAGE })

    expect(navigate).toHaveBeenCalledWith('/login', { replace: true, state: {} })
    expect(navigate).toHaveBeenCalledTimes(1)
  })
})

// NOTE — the survives-the-scrub case (CARRIED premortem #1: the discriminating test that actually
// forces capture-locally) lives in OAuthErrorBanner.survivesScrub.test.tsx, NOT here. It needs a
// REAL useNavigate so the scrub genuinely clears location.state mid-mount; this file mocks
// useNavigate to a no-op, so no in-file rerender can distinguish a captured banner from a live one
// (a MemoryRouter ignores changed initialEntries on rerender, and the no-op mock never clears the
// live state). Keeping that test real-router avoids a false sense of coverage here.

// Born-green BOUND — the scrub must NOT blank the banner on the current visit. This pins that the
// fix captures the message locally (not merely clears state); a green that "fixes" resurrection by
// hiding the banner outright would break this. Enabled: passes today (renders from live state).
describe('OAuthErrorBanner same-visit visibility (bound)', () => {
  it('shows the exact oauthError message on the current visit', () => {
    renderAt({ oauthError: MESSAGE })

    const banner = screen.getByTestId('login-oauth-error')
    expect(banner.textContent).toBe(MESSAGE)
    expect(banner).toHaveAttribute('role', 'alert')
  })
})

// Born-green DURABLE GUARANTEE — the whole point of the debt: a render reading a CLEARED location
// state shows NO banner. isUsableMessage already returns null for absent oauthError, so this is
// green today; it stays as the anti-resurrection guard the fix must preserve.
describe('OAuthErrorBanner anti-resurrection (guard)', () => {
  it('renders no banner when the location state has been cleared', () => {
    renderAt({})

    expect(screen.queryByTestId('login-oauth-error')).not.toBeInTheDocument()
  })
})
