import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { authorizedRequest, SessionExpiredError } from '../authorizedRequest'
import * as authSession from '../../utils/authSession'
import { clearSession, getAccessToken, saveSession } from '../../utils/authSession'

// The renewal path when renewal does NOT work. The happy path is covered in
// authorizedRequest.test.ts; what is exercised here is the set of exits that decide whether a
// signed-out user is told once, or whether the client sits in a retry loop against an endpoint
// that will never say yes — the failure mode that locks accounts.
function unauthorized() {
  return {
    ok: false,
    status: 401,
    json: async () => ({ error_code: 'INVALID_ACCESS_TOKEN', message: 'expired' }),
  }
}

function ok(body: unknown) {
  return { ok: true, status: 200, json: async () => body }
}

function refreshedTokens() {
  return ok({
    access_token: 'access-2',
    refresh_token: 'refresh-2',
    access_token_expires_at: '2026-07-17T00:15:00Z',
    refresh_token_expires_at: '2026-07-24T00:00:00Z',
  })
}

function isRefreshCall(call: unknown[]): boolean {
  return String(call[0]).includes('/auth/refresh')
}

describe('authorizedRequest when renewal fails', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  // The refresh token is gone (storage cleared in another tab, or a session saved without one).
  // There is nothing to renew with, so the request must end as a sign-out WITHOUT spending an
  // auth call to be told what is already known locally.
  it('signs the user out without calling refresh when there is no refresh token', async () => {
    saveSession({ accessToken: 'access-1', refreshToken: '' })
    const fetchMock = vi.fn().mockResolvedValue(unauthorized())
    vi.stubGlobal('fetch', fetchMock)

    await expect(authorizedRequest('/api/v1/generations')).rejects.toBeInstanceOf(
      SessionExpiredError,
    )

    expect(fetchMock.mock.calls.some(isRefreshCall)).toBe(false)
    expect(getAccessToken()).toBeNull()
  })

  // A rejected refresh ends the session rather than leaving tokens that will 401 again on the
  // next request — by which time the user has typed something they are about to lose.
  it('clears the session when the refresh call itself is rejected', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/auth/refresh')) {
        return Promise.resolve({ ok: false, status: 401, json: async () => ({ message: 'nope' }) })
      }
      return Promise.resolve(unauthorized())
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(authorizedRequest('/api/v1/generations')).rejects.toBeInstanceOf(
      SessionExpiredError,
    )

    expect(getAccessToken()).toBeNull()
  })

  // Persisting is part of succeeding. A token that cannot be stored is a token the next request
  // cannot send: it would 401, refresh, fail to store, and 401 again — an unbounded auth call per
  // request, invisible except as load on the auth endpoint.
  it('treats a token it cannot store as a sign-out instead of retrying forever', async () => {
    vi.spyOn(authSession, 'saveSession').mockReturnValue(false)
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/auth/refresh')) return Promise.resolve(refreshedTokens())
      return Promise.resolve(unauthorized())
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(authorizedRequest('/api/v1/generations')).rejects.toBeInstanceOf(
      SessionExpiredError,
    )

    expect(fetchMock.mock.calls.filter(isRefreshCall)).toHaveLength(1)
  })

  // The single-flight promise is module-global, so a FAILED renewal must not be the state every
  // later request inherits. It is cleared in `finally`; without that, one dead refresh would
  // sign out every subsequent request for the life of the tab even after the user signs back in.
  it('lets a later request renew again after an earlier renewal failed', async () => {
    const failing = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/auth/refresh')) {
        return Promise.resolve({ ok: false, status: 500, json: async () => ({}) })
      }
      return Promise.resolve(unauthorized())
    })
    vi.stubGlobal('fetch', failing)
    await expect(authorizedRequest('/api/v1/generations')).rejects.toBeInstanceOf(
      SessionExpiredError,
    )

    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
    const recovering = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (String(url).includes('/auth/refresh')) return Promise.resolve(refreshedTokens())
      const auth = (init?.headers as Record<string, string> | undefined)?.Authorization
      return Promise.resolve(auth === 'Bearer access-2' ? ok({ id: 'g-1' }) : unauthorized())
    })
    vi.stubGlobal('fetch', recovering)

    await expect(authorizedRequest('/api/v1/generations')).resolves.toEqual({ id: 'g-1' })
    expect(recovering.mock.calls.filter(isRefreshCall)).toHaveLength(1)
  })

  // Two requests expiring together share ONE refresh — the reason the single-flight exists. When
  // that shared renewal fails, BOTH must end as sign-outs; neither may replay with a dead token.
  it('fails both requests that shared one doomed renewal', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/auth/refresh')) {
        return Promise.resolve({ ok: false, status: 401, json: async () => ({}) })
      }
      return Promise.resolve(unauthorized())
    })
    vi.stubGlobal('fetch', fetchMock)

    const results = await Promise.allSettled([
      authorizedRequest('/api/v1/generations'),
      authorizedRequest('/api/v1/documents'),
    ])

    expect(results.map((r) => r.status)).toEqual(['rejected', 'rejected'])
    results.forEach((r) => {
      expect((r as PromiseRejectedResult).reason).toBeInstanceOf(SessionExpiredError)
    })
    expect(fetchMock.mock.calls.filter(isRefreshCall)).toHaveLength(1)
  })
})
