import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, render, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'
import * as authSession from '../../utils/authSession'

// Scenario 5.1 — the post-sign-in redirect target is validated. A crafted EXTERNAL redirect
// target is injected through every channel the callback could plausibly read (router `state.from`
// — the exact channel LoginForm reads — plus `?redirect=`/`?next=` query params, in absolute and
// protocol-relative form). On a successful sign-in the user must land on the in-app app-shell
// default ('/'), and the external host must NEVER reach navigate.
//
// BORN-GREEN: `goToApp` calls `navigate(safeRedirectTarget(undefined), { replace: true })` — it
// passes a hardcoded `undefined`, and the component never reads `state`, `?redirect`, or `?next`
// at all, so every crafted target is inert today. This test is a non-vacuous REGRESSION GUARD:
// pinning navigate to EXACTLY '/' means any future code that starts honoring the crafted target
// diverts navigate to the 'evil' host and flips this suite red.
//
// Seams mocked mirror OAuthCallback.success.test.tsx: the exchange api, authSession.saveSession,
// and useNavigate. safeRedirectTarget is left REAL — it is the guard under test.

const CODE = 'handoff-abc123'
const EVIL_ABSOLUTE = 'https://evil.example.com/steal'
const EVIL_PROTOCOL_RELATIVE = '//evil.example.com'
const EVIL_HTTPS = 'https://evil.example.com'
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

// Mount the callback with a valid code plus a crafted external target injected via `search` and/or
// router `state`, resolve the exchange, and let a usable session store succeed.
async function signInWith(entry: { pathname: string; search: string; state?: { from: string } }) {
  const exchange = deferred<typeof SESSION>()
  vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(exchange.promise)
  vi.mocked(authSession.saveSession).mockReturnValue(true)

  render(
    <MemoryRouter initialEntries={[entry]}>
      <OAuthCallback />
    </MemoryRouter>,
  )

  await act(async () => {
    exchange.resolve(SESSION)
    await exchange.promise
  })

  await waitFor(() => expect(authSession.saveSession).toHaveBeenCalledTimes(1))
}

// The scenario's defining property, asserted the same way for every channel: the WHOLE navigate
// call log is EXACTLY one call, to EXACTLY the app-shell default with replace-history — and no call
// (at any arity) ever carried the external host. Pinning `navigate.mock.calls` structurally is what
// gives this guard teeth: any future code that forwarded the crafted `from` — as a two-arg
// navigate, a bare single-arg navigate, or an extra call — changes the recorded log and flips red.
function expectLandedOnAppShellOnly() {
  expect(navigate.mock.calls).toEqual([['/', { replace: true }]])
  // Non-vacuous open-redirect guard, read off the ACTUAL recorded first-args (not
  // toHaveBeenCalledWith + expect.anything(), which silently passes a single-arg `navigate(evil)`
  // diversion because anything() never matches the absent second arg). Every injected EVIL_* value
  // contains 'evil', so a diversion to any of them would make this `.some(...)` true and fail here.
  const targets = navigate.mock.calls.map((call) => String(call[0]))
  expect(targets.some((target) => target.includes('evil'))).toBe(false)
}

describe('OAuthCallback redirect-target safety', () => {
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
    vi.mocked(authSession.saveSession).mockReset()
  })

  it('ignores an absolute external target in router state and lands on the app shell', async () => {
    await signInWith({
      pathname: '/auth/callback',
      search: `?code=${CODE}&provider=vk`,
      state: { from: EVIL_ABSOLUTE },
    })
    expectLandedOnAppShellOnly()
  })

  it('ignores a protocol-relative external target in router state', async () => {
    await signInWith({
      pathname: '/auth/callback',
      search: `?code=${CODE}&provider=vk`,
      state: { from: EVIL_PROTOCOL_RELATIVE },
    })
    expectLandedOnAppShellOnly()
  })

  it('ignores a bare https external target in router state', async () => {
    await signInWith({
      pathname: '/auth/callback',
      search: `?code=${CODE}&provider=vk`,
      state: { from: EVIL_HTTPS },
    })
    expectLandedOnAppShellOnly()
  })

  it('ignores an external target passed via the ?redirect query param', async () => {
    await signInWith({
      pathname: '/auth/callback',
      search: `?code=${CODE}&provider=vk&redirect=${EVIL_HTTPS}`,
    })
    expectLandedOnAppShellOnly()
  })

  it('ignores an external target passed via the ?next query param', async () => {
    await signInWith({
      pathname: '/auth/callback',
      search: `?code=${CODE}&provider=vk&next=${EVIL_HTTPS}`,
    })
    expectLandedOnAppShellOnly()
  })
})
