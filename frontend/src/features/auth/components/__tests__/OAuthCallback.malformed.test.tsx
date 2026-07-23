import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { OAuthCallback } from '../OAuthCallback'
import * as oauthExchangeApi from '../../api/oauthExchangeApi'
import * as authSession from '../../utils/authSession'

// Scenario 4.4 — the visitor lands on /auth/callback with a MALFORMED handoff, and the callback
// must resolve to the terminal error state WITHOUT ever issuing an exchange. Malformed means
// (spec 16_OAuthSignin.md:63-64): the provider is not exactly `vk`/`yandex`, OR the code is
// missing/empty, OR the code exceeds the client-side sanity cap (512 chars). Client-side
// pre-exchange validation runs AFTER the existing `?error=` guard and BEFORE the exchange POST.
//
// REAL RED — the current effect reads `code = searchParams.get('code') ?? ''`, ignores `provider`
// entirely, and fires `oauthExchange({ code })` unconditionally on the no-error path (even for an
// empty code, an unknown provider, or an over-length code). So each malformed case below currently
// DOES issue an exchange — every `not.toHaveBeenCalled()` assertion is expected to fail.
//
// Seams mirror the sibling OAuthCallback tests: useNavigate (routing side effect), oauthExchange
// (armed non-vacuously with a never-resolving promise so "not called" is a genuine observation,
// not a vacuous pass on an undefined stub that would make `.then` throw), authSession.saveSession
// (the storage side effect, a spy) and isAuthenticated pinned false (the visitor is not signed in).
//
// Positive control: a WELL-FORMED callback (?code=goodcode&provider=vk) DOES fire the exchange —
// that is the happy path already covered by OAuthCallback.success.test.tsx, so it is not re-fired
// here. This file asserts only the negative: malformed → error state, no exchange.

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
  return { ...actual, saveSession: vi.fn(), isAuthenticated: () => false }
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

function assertMalformed() {
  // No spendable handoff — the exchange POST must never be sent for a malformed callback.
  expect(oauthExchangeApi.oauthExchange).not.toHaveBeenCalled()
  // The terminal error card is shown, and the transient spinner does not persist.
  expect(screen.getByTestId('oauth-callback-error')).toBeInTheDocument()
  expect(screen.queryByTestId('oauth-callback-loading')).not.toBeInTheDocument()
  // Nothing was stored and no navigation happened — the visitor rests on the error state.
  expect(authSession.saveSession).not.toHaveBeenCalled()
  expect(navigate).not.toHaveBeenCalled()
}

describe('OAuthCallback malformed-callback validation', () => {
  beforeEach(() => {
    // Arm the exchange spy non-vacuously so "not called" is a genuine observation, not a
    // vacuous pass on an undefined stub whose absent `.then` would throw.
    vi.mocked(oauthExchangeApi.oauthExchange).mockReturnValue(neverResolves())
  })

  afterEach(() => {
    navigate.mockReset()
    vi.mocked(oauthExchangeApi.oauthExchange).mockReset()
    vi.mocked(authSession.saveSession).mockReset()
  })

  // provider is not in the valid {vk, yandex} set → malformed, no exchange.
  it('shows the error state and fires no exchange for an unknown provider', () => {
    renderAtCallback('?code=goodcode&provider=foo')

    assertMalformed()
  })

  // code present but empty (`?code=`) → malformed, no exchange.
  it('shows the error state and fires no exchange for an empty code', () => {
    renderAtCallback('?code=&provider=vk')

    assertMalformed()
  })

  // code param absent entirely → malformed, no exchange.
  it('shows the error state and fires no exchange for a missing code', () => {
    renderAtCallback('?provider=vk')

    assertMalformed()
  })

  // code exceeds the 512-char client-side sanity cap → malformed, no exchange.
  it('shows the error state and fires no exchange for an over-length code', () => {
    renderAtCallback(`?code=${'x'.repeat(513)}&provider=vk`)

    assertMalformed()
  })

  // POSITIVE control (guards `>` vs `>=` off-by-one): a code of EXACTLY 512 chars is at the cap and
  // therefore VALID — the exchange DOES fire with { code } and no error card is shown. The exchange
  // spy returns a never-resolving promise so the component stays on the loading state.
  it('fires the exchange for a code at exactly the 512-char cap', () => {
    const code = 'x'.repeat(512)

    renderAtCallback(`?code=${code}&provider=vk`)

    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledTimes(1)
    expect(oauthExchangeApi.oauthExchange).toHaveBeenCalledWith({ code })
    expect(screen.queryByTestId('oauth-callback-error')).not.toBeInTheDocument()
  })

  // Whitespace-only code (guards trim() vs `=== ''`): `?code=%20%20%20` is blank once trimmed →
  // malformed, no exchange.
  it('shows the error state and fires no exchange for a whitespace-only code', () => {
    renderAtCallback('?code=%20%20%20&provider=vk')

    assertMalformed()
  })
})
