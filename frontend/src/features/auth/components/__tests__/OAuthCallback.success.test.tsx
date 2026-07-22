import { describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'
import * as authSession from '../../utils/authSession'

// Scenario 3.1 — the visitor lands on /auth/callback with a VALID one-time handoff code. The
// callback screen shows a loading state while POST /oauth/exchange is in flight, and on a valid
// session it stores the tokens and takes the user to the authenticated app shell, REPLACING
// history so Back does not walk back onto the callback interstitial.
//
// REAL RED — OAuthCallback and oauthExchangeApi do not exist yet; this drives them into being.
// The imports of both are DYNAMIC (inside the test) and the suite is describe.skip, mirroring
// AppRouting.test.tsx: a static import of a not-yet-existing module crashes collection even under
// skip, so `.skip` only truly suppresses resolution when the import is deferred. green-frontend
// un-skips (and switches to static imports) once the two modules land.
//
// Seams mocked (mirrors VerifyCodeForm.success.test.tsx): the exchange api (no real fetch; the
// component's contract with it is the only thing under test), authSession.saveSession (the storage
// side effect), and useNavigate (the landing side effect). safeRedirectTarget is left REAL — with
// no crafted redirect target present it resolves the in-app default '/', which is the
// "authenticated app shell" this scenario lands on. 5.1 pins the crafted-target case.
//
// HAPPY PATH only. exactly-once-under-double-mount (3.2), late-duplicate (3.3),
// error/replay/network (4.x) and the redirect-target edge (5.1) are their own scenarios.

const CODE = 'handoff-abc123'
// A distinctive session sentinel. The exchange really maps the /auth/login body shape, but it is
// mocked here — the test's job is to prove the component pipes the returned tokens into
// authSession and does not fabricate its own.
const SESSION = {
  accessToken: 'acc-9f3ab',
  refreshToken: 'ref-7b2cd',
  accessTokenExpiresAt: '2026-07-22T10:00:00Z',
  refreshTokenExpiresAt: '2026-07-29T10:00:00Z',
}

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
  return { ...actual, saveSession: vi.fn() }
})

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

// RED: OAuthCallback + oauthExchangeApi do not exist yet — skipped so the suite stays green
// between red and green. green-frontend un-skips after the component + exchange api land.
// RED: OAuthCallback + oauthExchangeApi are empty stubs — skipped so the suite stays green
// between red and green. green-frontend un-skips after implementing the loading + exchange flow.
describe.skip('OAuthCallback success flow', () => {
  it('shows loading, exchanges the code once, stores the session and replaces history to the app shell', async () => {
    navigate.mockReset()

    const exchange = deferred<typeof SESSION>()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(exchange.promise)
    vi.mocked(authSession.saveSession).mockReturnValue(true)

    render(
      <MemoryRouter initialEntries={[`/auth/callback?code=${CODE}&provider=vk`]}>
        <OAuthCallback />
      </MemoryRouter>,
    )

    // While the exchange is in flight, the interstitial shows a loading state — NOT a resolved
    // screen and NOT yet a navigation. The mockup's promise: a transient spinner, never hung.
    expect(screen.getByTestId('oauth-callback-loading')).toBeInTheDocument()
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: CODE })
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(navigate).not.toHaveBeenCalled()

    await act(async () => {
      exchange.resolve(SESSION)
      await exchange.promise
    })

    // The returned tokens are what get stored — the component maps the exchange body into the
    // AuthSession shape rather than inventing values.
    await waitFor(() =>
      expect(authSession.saveSession).toHaveBeenCalledWith({
        accessToken: SESSION.accessToken,
        refreshToken: SESSION.refreshToken,
      }),
    )
    // Exactly one store — a double-store (e.g. an effect firing twice) must fail here, not pass.
    expect(authSession.saveSession).toHaveBeenCalledTimes(1)
    // The scenario's defining property: land on the in-app app shell default ('/', from the REAL
    // safeRedirectTarget with no crafted target), replacing history so Back does not return here.
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })
    // ...and land there exactly once — a stray second navigation must fail, not pass.
    expect(navigate).toHaveBeenCalledTimes(1)
  })
})
