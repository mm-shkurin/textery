import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'

// Scenario 4.5 — the visitor lands on /auth/callback with an UNRECOGNIZED `?error=<weird_code>`
// (a value the app has no specific copy for) and no provider hint. The callback must fall back to
// the GENERIC sign-in-failed copy, and the raw error value must NEVER leak — not into the router
// state it emits, and not onto the screen (spec 16_OAuthSignin.md:56, tests/02_UI_Tests.md:113-118).
//
// This is a GUARD test. The shipped 4.1 implementation maps the failure message on the PROVIDER and
// treats `error` only as a presence trigger — the raw error value is never mapped or rendered — so
// this behavior is BORN-GREEN. The test pins the guarantee so a future change that starts
// interpolating the raw error code (a reflected-value regression) fails loudly.
//
// Seams mirror OAuthCallback.providerError.test.tsx: useNavigate (the routing side effect) and
// oauthExchange (armed non-vacuously so "not called" is a real observation).

const GENERIC_ERROR_MESSAGE = 'Не удалось войти через провайдера. Попробуйте снова.'
const RAW_ERROR_CODE = 'totally_unknown_xyz'

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../../api/oauthExchangeApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/oauthExchangeApi')>()
  return { ...actual, oauthExchange: vi.fn() }
})

function neverResolves<T>() {
  return new Promise<T>(() => {})
}

function renderAtCallback(query: string) {
  return render(
    <MemoryRouter initialEntries={[`/auth/callback${query}`]}>
      <OAuthCallback />
    </MemoryRouter>,
  )
}

describe('OAuthCallback unrecognized error code fallback', () => {
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
  })

  it('falls back to the generic message and never emits or renders the raw error value', () => {
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(neverResolves())

    renderAtCallback(`?error=${RAW_ERROR_CODE}`)

    // No code to spend on the error path — the exchange POST must never be sent (exactly zero times).
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(0)

    // Returned to /login, history replaced, carrying the GENERIC fallback copy — exact string.
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/login', {
      replace: true,
      state: { oauthError: GENERIC_ERROR_MESSAGE },
    })

    // The raw error value must NEVER be reflected into the emitted router state.
    const [, options] = navigate.mock.calls[0]
    expect(options.state.oauthError).toBe(GENERIC_ERROR_MESSAGE)
    expect(options.state.oauthError).not.toContain(RAW_ERROR_CODE)

    // The transient spinner must not persist, and the raw error value must not appear on screen.
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()

    // Positive control — the on-screen leak probe is only meaningful if it CAN see the raw value.
    // On the error path the callback renders null, so `body.textContent` is empty and a bare
    // `.not.toContain` would pass vacuously (it can never catch a leak because nothing is rendered).
    // Inject the raw value, prove the SAME probe catches it, then remove it — so the assertion that
    // follows is a real observation about the callback's output, not a vacuous pass on an empty DOM.
    const leakControl = document.createElement('div')
    leakControl.textContent = RAW_ERROR_CODE
    document.body.appendChild(leakControl)
    expect(document.body.textContent ?? '').toContain(RAW_ERROR_CODE)
    document.body.removeChild(leakControl)

    // Control removed: the raw error value the callback itself rendered is genuinely absent.
    expect(document.body.textContent ?? '').not.toContain(RAW_ERROR_CODE)
  })
})
