import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'
import * as authSession from '../../utils/authSession'

// Scenario 3.3 — a LATE duplicate rejection after a stored success is ignored.
//
// `hasExchanged` is a per-INSTANCE useRef. A genuine remount of the callback route (Back/Forward,
// re-navigation → a fresh Router, hence a fresh ref) fires a SECOND POST /oauth/exchange with the
// now-spent one-time code. The backend rejects it as already-used. But the FIRST mount already
// stored a valid session — the user is authenticated. The rejection is benign: it must NOT bounce
// an already-signed-in user onto the terminal error screen.
//
// Required behaviour (design already decided): on an exchange REJECTION the callback distinguishes
// "already authenticated" from "genuinely failed". With a session present (`isAuthenticated()` →
// true) the rejection is a duplicate → navigate to the app shell ('/', replace) and DO NOT render
// `oauth-callback-error`. Only an UNauthenticated rejection shows the error state.
//
// Seams mirror OAuthCallback.exactlyOnce.test.tsx (useNavigate, oauthExchange, authSession) —
// except `isAuthenticated` is controllable here and pinned true for the main test. safeRedirectTarget
// is left REAL so the landing target is the in-app default '/'.

const CODE = 'handoff-dup-33'

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

function renderCallback() {
  return render(
    <MemoryRouter initialEntries={[`/auth/callback?code=${CODE}&provider=vk`]}>
      <OAuthCallback />
    </MemoryRouter>,
  )
}

describe('OAuthCallback late duplicate rejection', () => {
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
    vi.mocked(authSession.saveSession).mockReset()
    vi.mocked(authSession.isAuthenticated).mockReset()
  })

  // A second exchange for a spent code rejects, but the first mount already stored a session.
  // The already-authenticated user stays in the app shell; no bounce to the error screen.
  // RED (Scenario 3.3): current `.catch` calls setFailed(true) unconditionally with no
  // isAuthenticated branch → navigate is never called (0 times, expected 1) and the error screen
  // renders. Skipped until green-frontend adds the authenticated-rejection branch.
  it('lands on the app shell and hides the error state when a duplicate exchange rejects while authenticated', async () => {
    const rejection = Promise.reject(new Error('handoff code already used'))
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(rejection)
    vi.mocked(authSession.isAuthenticated).mockReturnValue(true)
    // Swallow the terminal rejection so it is not flagged as unhandled once `.catch` consumes it.
    const settled = rejection.catch(() => undefined)

    renderCallback()

    await act(async () => {
      await settled
    })

    // The duplicate exchange fired exactly once for the spent code and rejected.
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: CODE })
    // Non-vacuous seam: the benign-vs-fatal decision MUST be driven by the session check.
    // An unconditional redirect on `.catch` (ignoring isAuthenticated) would satisfy the
    // navigate assertions below while defeating the scenario — pin that the branch consulted it.
    expect(authSession.isAuthenticated).toHaveBeenCalledTimes(1)
    // Nothing is stored on the rejection path — the FIRST mount already owns the session.
    expect(authSession.saveSession).not.toHaveBeenCalled()

    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })
    expect(screen.queryByTestId('oauth-callback-error')).not.toBeInTheDocument()
  })
})
