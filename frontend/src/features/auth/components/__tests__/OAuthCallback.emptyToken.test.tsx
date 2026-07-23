import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'
import * as authSession from '../../utils/authSession'
import { sessionTokensFromWire, type SessionTokens } from '../../api/sessionTokens'

// Scenario 4.6 — a 200 exchange WITHOUT a usable token must fail closed. The visitor lands on
// /auth/callback with a VALID handoff code; the exchange RESOLVES 200 (not a rejection — the 4.x
// network/replay paths never fire), but the body carries no spendable access token: it is absent,
// null, or empty. Spec 16_OAuthSignin.md:67 + Notes:55-56 — "a 200 missing a usable token is an
// error, not a sign-in"; reject only on a MISSING usable token, never on an unexpected present one.
// Required behaviour: NO session is stored (saveSession never fires), the user is NEVER taken to the
// app shell (no navigate('/', …)), and the terminal login error card is shown instead of a hung
// spinner — mirroring the store-refused fail-closed arm the success test already pins.
//
// Seams mirror the sibling OAuthCallback tests: useNavigate, oauthExchange, and authSession.saveSession.
// sessionTokensFromWire is left REAL (unmocked) so cases 1 & 2 pin that the '' collapse the mapper
// performs on an absent/null access_token is exactly what reaches the component's guard.

const CODE = 'handoff-abc123'

// A fully usable session for the born-green positive control — a real access token still signs in.
const GOOD_SESSION: SessionTokens = {
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

// Render the callback with a valid code, resolve the (mocked) exchange with the given session, and
// settle the component's `.then`. saveSession is ARMED to return true so the negative assertions are
// non-vacuous: if the token-usability guard were absent, a truthy store would carry the visitor onto
// the app shell — the very bug 4.6 forbids — and the assertions would (correctly) fail.
async function renderAndResolve(session: SessionTokens) {
  const exchange = deferred<SessionTokens>()
  vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(exchange.promise)
  vi.mocked(authSession.saveSession).mockReturnValue(true)

  render(
    <MemoryRouter initialEntries={[`/auth/callback?code=${CODE}&provider=vk`]}>
      <OAuthCallback />
    </MemoryRouter>,
  )

  await act(async () => {
    exchange.resolve(session)
    await exchange.promise
  })
}

// Assert the fail-closed contract: nothing stored, never the app shell, terminal error card shown.
async function expectFailedClosed() {
  // Non-vacuous: the real component parsed the code and drove the exchange seam, so the resolved
  // session under test genuinely flows through the component — not an unrelated early return.
  expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
  expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code: CODE })
  // No session is stored — a token-less 200 is not a sign-in.
  expect(authSession.saveSession).not.toHaveBeenCalled()
  // Never the app shell, and in fact no navigation at all — the visitor stays on the error state.
  expect(navigate).not.toHaveBeenCalledWith('/', { replace: true })
  expect(navigate).not.toHaveBeenCalled()
  // The terminal login error card is shown instead of a hung spinner.
  await waitFor(() => expect(screen.getByTestId('oauth-callback-error')).toBeInTheDocument())
  expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
}

describe('OAuthCallback 200-without-usable-token fail-closed', () => {
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
    vi.mocked(authSession.saveSession).mockReset()
  })

  // RED: the access token is ABSENT from the wire body — the REAL sessionTokensFromWire collapses it
  // to accessToken:''. Current code has no usability guard: it calls saveSession({accessToken:'', …}),
  // the armed store returns true, and it navigates to the app shell '/'. Skipped until green-frontend
  // adds the missing-usable-token guard.
  it('fails closed when the exchange 200 body has no access_token (real wire mapping)', async () => {
    const session = sessionTokensFromWire({
      refresh_token: 'ref-abc',
      access_token_expires_at: '2026-07-22T10:00:00Z',
      refresh_token_expires_at: '2026-07-29T10:00:00Z',
    })

    await renderAndResolve(session)

    await expectFailedClosed()
  })

  // RED: access_token is explicitly null on the wire — REAL sessionTokensFromWire collapses null to
  // accessToken:'' via `?? ''`. Same missing-usable-token failure as the absent case.
  it('fails closed when the exchange 200 body has a null access_token (real wire mapping)', async () => {
    const session = sessionTokensFromWire({
      access_token: null,
      refresh_token: 'ref-abc',
    })

    await renderAndResolve(session)

    await expectFailedClosed()
  })

  // RED: access token is an empty string in the resolved session shape — an unusable credential just
  // like absent/null. Driven via the camelCase session directly to pin the guard triggers regardless
  // of the token's provenance (wire vs. already-mapped).
  it('fails closed when the exchange 200 session has an empty-string access token', async () => {
    const session: SessionTokens = {
      accessToken: '',
      refreshToken: 'ref-abc',
      accessTokenExpiresAt: '2026-07-22T10:00:00Z',
      refreshTokenExpiresAt: '2026-07-29T10:00:00Z',
    }

    await renderAndResolve(session)

    await expectFailedClosed()
  })

  // A whitespace-only access token is truthy but unspendable — a bare `if (!session.accessToken)`
  // check would wrongly sign it in. The guard uses `/\S/` so blank-but-present tokens fail closed too
  // (carried premortem finding: whitespace-only truthy token).
  it('fails closed when the exchange 200 session has a whitespace-only access token', async () => {
    const session: SessionTokens = {
      accessToken: '   ',
      refreshToken: 'ref-abc',
      accessTokenExpiresAt: '2026-07-22T10:00:00Z',
      refreshTokenExpiresAt: '2026-07-29T10:00:00Z',
    }

    await renderAndResolve(session)

    await expectFailedClosed()
  })

  // BOUNDING GUARD (born-green): a 200 WITH a usable access token still stores the session and lands
  // on the app shell, replacing history. This stops a 4.6 green from over-broadly treating EVERY 200
  // as token-less and failing every sign-in. Current code already signs in here, so this passes today.
  it('signs in and lands on the app shell when the 200 carries a usable access token', async () => {
    await renderAndResolve(GOOD_SESSION)

    await waitFor(() =>
      expect(authSession.saveSession).toHaveBeenCalledWith({
        accessToken: GOOD_SESSION.accessToken,
        refreshToken: GOOD_SESSION.refreshToken,
      }),
    )
    expect(authSession.saveSession).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(screen.queryByTestId('oauth-callback-error')).not.toBeInTheDocument()
  })
})
