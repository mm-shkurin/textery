import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'
import * as authSession from '../../utils/authSession'

// Scenario 4.3 — a REPLAYED or EXPIRED handoff code shows an error, NOT a second sign-in.
//
// The visitor re-opens /auth/callback with an already-used handoff code, in a tab where NO session
// exists (unauthenticated — distinct from 3.3, the AUTHENTICATED late-duplicate that redirects to
// the shell). The exchange rejects the code as used/expired with a BUSINESS error
// (`INVALID_OR_EXPIRED_OAUTH_CODE`, carrying an errorCode, no 5xx). Required behaviour: land on the
// terminal `oauth-callback-error` screen and — the crux of 4.3 — create NO session and trigger NO
// sign-in (no saveSession, no navigate).
//
// BORN-GREEN: the current `.catch` already handles this. Unauthenticated (isAuthenticated → false)
// + non-network business rejection (isLoginNetworkError → false) falls through to setFailed(true),
// and saveSession / navigate are never reached on the reject path. The 4.2 bounding guard already
// pinned navigate-not-called + error-shown for this shape; this test adds the invariant 4.2 did NOT
// assert — saveSession NOT called (no new session on a replay).
//
// Seams mirror the sibling OAuthCallback tests: useNavigate, oauthExchange, and authSession with
// isAuthenticated pinned false and saveSession spied to prove the replay stores nothing.

const CODE = 'already-used-xyz'

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../../api/oauthExchangeApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/oauthExchangeApi')>()
  return { ...actual, oauthExchange: vi.fn() }
})

vi.mock('../../utils/authSession', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../utils/authSession')>()
  return { ...actual, saveSession: vi.fn(), isAuthenticated: vi.fn() }
})

function renderAtCallback() {
  return render(
    <MemoryRouter initialEntries={[`/auth/callback?code=${CODE}&provider=vk`]}>
      <OAuthCallback />
    </MemoryRouter>,
  )
}

describe('OAuthCallback replayed / expired code', () => {
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
    vi.mocked(authSession.saveSession).mockReset()
    vi.mocked(authSession.isAuthenticated).mockReset()
  })

  // A used/expired code rejects as a business error in an unauthenticated tab. The terminal error
  // screen shows; no session is created and no sign-in fires. Born-green — the current `.catch`
  // falls through to setFailed(true) for a non-network unauthenticated rejection, leaving both
  // saveSession and navigate untouched.
  it('shows the error screen and creates no session on a replayed / expired code', async () => {
    vi.mocked(authSession.isAuthenticated).mockReturnValue(false)
    const rejection = Promise.reject({
      errorCode: 'INVALID_OR_EXPIRED_OAUTH_CODE',
      message: 'Код входа истёк',
    })
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(rejection as Promise<never>)
    // Swallow the terminal rejection so it is not flagged as unhandled once `.catch` consumes it.
    const settled = rejection.catch(() => undefined)

    renderAtCallback()

    await act(async () => {
      await settled
    })

    // Non-vacuous: the replay attempt actually fired for the spent code — the rejection under test
    // genuinely flows from oauthExchange, not from an unrelated early return.
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: CODE })
    // The terminal error card is shown and the spinner is gone — no indefinite spinner.
    expect(await screen.findByTestId('oauth-callback-error')).toBeInTheDocument()
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
    // The core 4.3 invariant: no new session is created on a replayed code.
    expect(authSession.saveSession).not.toHaveBeenCalled()
    // No second sign-in, no redirect.
    expect(navigate).not.toHaveBeenCalled()
  })
})
