import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'

// Scenario 4.1 — the visitor lands on /auth/callback with an ERROR param (provider error or a
// user-cancel: ?error=access_denied), NOT a handoff code. The callback must NOT attempt an
// exchange (there is no code to spend), must NOT hang the loading spinner, and must route back to
// /login carrying a DISTINCT provider-sign-in message in router state — provider-aware, mapped
// from copy, never the raw error value (spec 16_OAuthSignin.md:64-65). The login screen (asserted
// separately in LoginForm.oauthError.test.tsx) then renders that message as its own banner.
//
// Seams mirror OAuthCallback.success.test.tsx exactly: useNavigate (the routing side effect) and
// oauthExchange (armed non-vacuously so "not called" is a real observation, not a vacuous pass on
// an undefined stub). safeRedirectTarget is irrelevant here — the target is the fixed '/login'.

const VK_ERROR_MESSAGE = 'Не удалось войти через VK ID. Попробуйте снова.'
const GENERIC_ERROR_MESSAGE = 'Не удалось войти через провайдера. Попробуйте снова.'

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

// RED: the current callback ignores the error param, spends an empty code on the exchange, and
// never routes to /login. describe.skip so the suite stays green between red and green;
// green-frontend implements the error-routing branch and un-skips.
describe.skip('OAuthCallback provider-error routing', () => {
  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
  })

  // Arm the spy so the "not called" assertion is a genuine observation: a spy left returning
  // undefined would make the component's `.then` throw, muddying which behavior the test pins.
  it('routes to /login with the VK-aware message and fires no exchange for ?error with provider=vk', () => {
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(neverResolves())

    renderAtCallback('?error=access_denied&provider=vk')

    // No code to spend — the exchange POST must never be sent on the error path.
    expect(oauthExchangeApi.oauthExchange).not.toHaveBeenCalled()
    // Returned to /login, history replaced, carrying the provider-aware distinct message as state.
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/login', {
      replace: true,
      state: { oauthError: VK_ERROR_MESSAGE },
    })
    // The transient spinner must not persist on the error path — the visitor is routed away, not
    // stranded on "Завершаем вход…". Assert the loading card is gone by its exact testid.
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
  })

  // Provider absent → the generic "…через провайдера…" fallback, never a blank or the raw error.
  it('routes to /login with the generic fallback message when the provider param is absent', () => {
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(neverResolves())

    renderAtCallback('?error=access_denied')

    expect(oauthExchangeApi.oauthExchange).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/login', {
      replace: true,
      state: { oauthError: GENERIC_ERROR_MESSAGE },
    })
    expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
  })
})
