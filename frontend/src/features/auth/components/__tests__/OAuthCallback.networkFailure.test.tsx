import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'
import * as authSession from '../../utils/authSession'
import { NETWORK_LOGIN_FAILURE_MESSAGE } from '../../utils/authMessages'
import { RequestTimeoutError } from '../../../../shared/api/httpClient'

// Scenario 4.2 — the visitor lands on /auth/callback with a VALID handoff code, but the exchange
// fails with a NETWORK / TIMEOUT / SERVER (5xx) error. This is the UNauthenticated first-sign-in
// path: no session was ever stored, so `isAuthenticated()` is false. Required behaviour (design
// already decided): on a TRANSPORT-shaped or GATEWAY-5xx rejection the callback returns the visitor
// to /login carrying a RETRY-capable banner message — the same channel scenario 4.1 built:
// navigate('/login', { replace: true, state: { oauthError: NETWORK_LOGIN_FAILURE_MESSAGE } }) —
// and the indefinite spinner is never left on screen. The classifier is the EXISTING
// `isLoginNetworkError` (no `errorCode` → transport; OR codeless body with status >= 500 → gateway).
//
// The BOUNDING guard (case 3) pins that a genuine BUSINESS rejection (has errorCode, no 5xx) stays
// on the TERMINAL error screen — it must NOT be swept to /login, which would swallow 4.3's case.
//
// Seams mirror the sibling OAuthCallback tests: useNavigate, oauthExchange, and authSession with
// isAuthenticated pinned false (unauthenticated first sign-in) and saveSession spied to prove the
// rejection path never stores. NETWORK_LOGIN_FAILURE_MESSAGE is imported from the REAL (unmocked)
// authMessages so the assertion pins the exact copy the login banner will render.

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
    <MemoryRouter initialEntries={['/auth/callback?code=valid-abc&provider=vk']}>
      <OAuthCallback />
    </MemoryRouter>,
  )
}

// Reject with the given shape, settle the component's `.catch`, and swallow the rejection so it is
// not flagged as unhandled once `.catch` consumes it.
async function renderAndSettleRejection(reason: unknown) {
  const rejection = Promise.reject(reason)
  vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(rejection as Promise<never>)
  const settled = rejection.catch(() => undefined)

  renderAtCallback()

  await act(async () => {
    await settled
  })
}

// RED (Scenario 4.2): cases 1 & 2 fail — current `.catch` calls setFailed(true) unconditionally on
// the unauthenticated path, so navigate is never called (0 times, expected 1) and the terminal
// error card renders instead of routing to /login. Case 3 is the born-green bounding guard.
// Skipped until green-frontend adds the isLoginNetworkError branch that routes transport/5xx
// failures to /login with NETWORK_LOGIN_FAILURE_MESSAGE.
describe('OAuthCallback network / server exchange failure', () => {
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
    vi.mocked(authSession.saveSession).mockReset()
    vi.mocked(authSession.isAuthenticated).mockReset()
  })

  // RED: a transport-shaped rejection (bare Error, no errorCode) on the unauthenticated path must
  // route back to /login with the retry-capable banner, not strand the visitor on the terminal
  // error card. Current `.catch` calls setFailed(true) unconditionally → navigate never fires
  // (0 times, expected 1) and oauth-callback-error renders. Skipped until green-frontend adds the
  // isLoginNetworkError branch.
  it('returns to /login with a retry-capable message on a transport-shaped exchange failure', async () => {
    vi.mocked(authSession.isAuthenticated).mockReturnValue(false)

    await renderAndSettleRejection(new Error('Failed to fetch'))

    // Non-vacuous: the real component parsed the URL code and drove the exchange seam, so the
    // rejection under test genuinely flows from oauthExchange — not from an unrelated early return.
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: 'valid-abc' })
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/login', {
      replace: true,
      state: { oauthError: NETWORK_LOGIN_FAILURE_MESSAGE },
    })
    // Not stranded on the spinner, and not on the terminal error card either — routed away.
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
    expect(screen.queryByTestId('oauth-callback-error')).not.toBeInTheDocument()
    // Nothing was stored — the exchange never resolved a session.
    expect(authSession.saveSession).not.toHaveBeenCalled()
  })

  // RED: a gateway 5xx (codeless UNKNOWN_ERROR body carrying status 503) is a transport-class
  // failure too — isLoginNetworkError is true via the status >= 500 branch. Same routing to /login
  // with the retry banner. Current code shows the terminal error instead.
  it('returns to /login with a retry-capable message on a gateway 5xx exchange failure', async () => {
    vi.mocked(authSession.isAuthenticated).mockReturnValue(false)

    await renderAndSettleRejection({ errorCode: 'UNKNOWN_ERROR', message: '', status: 503 })

    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: 'valid-abc' })
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/login', {
      replace: true,
      state: { oauthError: NETWORK_LOGIN_FAILURE_MESSAGE },
    })
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
    expect(screen.queryByTestId('oauth-callback-error')).not.toBeInTheDocument()
    expect(authSession.saveSession).not.toHaveBeenCalled()
  })

  // RED (folded from the 4.2 premortem CONCERN): a RequestTimeoutError — the httpClient's transport
  // timeout, carrying NO errorCode and NO status — is retry-affording too. It reaches isLoginNetworkError
  // via the SAME `!errorCode` transport arm as the bare-Error case, but pinning it independently proves
  // the TIMEOUT shape routes to /login and is not accidentally coupled to a plain Error's identity.
  it('returns to /login with a retry-capable message on a RequestTimeoutError exchange failure', async () => {
    vi.mocked(authSession.isAuthenticated).mockReturnValue(false)

    await renderAndSettleRejection(new RequestTimeoutError())

    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: 'valid-abc' })
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/login', {
      replace: true,
      state: { oauthError: NETWORK_LOGIN_FAILURE_MESSAGE },
    })
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
    expect(screen.queryByTestId('oauth-callback-error')).not.toBeInTheDocument()
    expect(authSession.saveSession).not.toHaveBeenCalled()
  })

  // BOUNDING GUARD (born-green): a genuine BUSINESS rejection (has errorCode, no 5xx →
  // isLoginNetworkError false) while unauthenticated must STAY on the terminal error screen, never
  // routed to /login. This stops a 4.2 green from over-broadly sweeping EVERY failure to login,
  // which would wrongly swallow 4.3's replayed/expired-code terminal-error case. Current code
  // already renders the terminal error here, so this passes today.
  it('keeps a business rejection on the terminal error screen and does not route to /login', async () => {
    vi.mocked(authSession.isAuthenticated).mockReturnValue(false)

    await renderAndSettleRejection({ errorCode: 'INVALID_OR_EXPIRED_OAUTH_CODE', message: 'expired' })

    // The terminal error card proves it was THIS rejection that rendered, not a vacuous early exit:
    // the exchange fired and the classifier bounded it away from the /login retry channel.
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: 'valid-abc' })
    expect(navigate).not.toHaveBeenCalled()
    expect(await screen.findByTestId('oauth-callback-error')).toBeInTheDocument()
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
  })
})
