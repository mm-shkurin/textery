import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { IdentityUnavailableError, identityRequest } from '../identityRequest'
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  saveSession,
} from '../../../../features/auth/utils/authSession'

// The rule this module exists for: a read that fires unprompted on every authenticated page must
// never conclude the session is dead. `performRenewal` calls `clearSession()` on ANY renewal
// failure, which is right for a request the user made and catastrophic here — one blip during a
// rolling deploy would sign out every open tab and take the unsaved editor text with it.
//
// So every failure below asserts TWO things: what the caller sees, and that the stored tokens
// were left alone. The second half is the one that matters.

function ok(body: unknown) {
  return { ok: true, status: 200, json: async () => body, blob: async () => new Blob([]) }
}

function status(code: number) {
  return { ok: false, status: code, json: async () => ({ error_code: 'NOPE', message: 'no' }) }
}

function refreshed(suffix: string) {
  return ok({
    access_token: `access-${suffix}`,
    refresh_token: `refresh-${suffix}`,
    access_token_expires_at: '2026-08-14T00:15:00Z',
    refresh_token_expires_at: '2026-08-21T00:00:00Z',
  })
}

function isRefreshCall(call: unknown[]): boolean {
  return String(call[0]).includes('/auth/refresh')
}

describe('identityRequest', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('attaches the access token', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({ email: 'ada@example.ru' }))
    vi.stubGlobal('fetch', fetchMock)

    await identityRequest('/api/v1/auth/me')

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer access-1')
  })

  it('keeps the caller-supplied options and adds the header to them', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({}))
    vi.stubGlobal('fetch', fetchMock)

    await identityRequest('/api/v1/auth/me/avatar', {
      responseType: 'blob',
      headers: { Accept: 'image/webp' },
    })

    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({
      Accept: 'image/webp',
      Authorization: 'Bearer access-1',
    })
  })

  it('refuses before calling the API when there is no token', async () => {
    clearSession()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    await expect(identityRequest('/api/v1/auth/me')).rejects.toBeInstanceOf(
      IdentityUnavailableError,
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('renews once on a 401 and replays the request', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(status(401))
      .mockResolvedValueOnce(refreshed('2'))
      .mockResolvedValueOnce(ok({ email: 'ada@example.ru' }))
    vi.stubGlobal('fetch', fetchMock)

    const body = await identityRequest<{ email: string }>('/api/v1/auth/me')

    expect(body.email).toBe('ada@example.ru')
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer access-2')
    expect(getAccessToken()).toBe('access-2')
  })

  it('replays with a token another request already renewed instead of spending a refresh', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (isRefreshCall([url])) throw new Error('should not have refreshed')
      // The first attempt 401s; by then a concurrent request has stored a newer token.
      if (fetchMock.mock.calls.length === 1) {
        saveSession({ accessToken: 'access-concurrent', refreshToken: 'refresh-1' })
        return Promise.resolve(status(401))
      }
      return Promise.resolve(ok({ email: 'ada@example.ru' }))
    })
    vi.stubGlobal('fetch', fetchMock)

    await identityRequest('/api/v1/auth/me')

    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer access-concurrent')
  })

  it('retries exactly once — a 401 on a brand-new token is not staleness', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(status(401))
      .mockResolvedValueOnce(refreshed('2'))
      .mockResolvedValueOnce(status(401))
    vi.stubGlobal('fetch', fetchMock)

    await expect(identityRequest('/api/v1/auth/me')).rejects.toBeInstanceOf(
      IdentityUnavailableError,
    )
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })
})

describe('what identityRequest must never do to the session', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function expectSessionIntact() {
    expect(getAccessToken()).toBe('access-1')
    expect(getRefreshToken()).toBe('refresh-1')
  }

  it.each([500, 502, 503, 404, 400])('leaves the session alone on a %i', async (code) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(status(code)))

    await expect(identityRequest('/api/v1/auth/me')).rejects.toBeInstanceOf(
      IdentityUnavailableError,
    )
    expectSessionIntact()
  })

  it('leaves the session alone when the network is down', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(identityRequest('/api/v1/auth/me')).rejects.toBeInstanceOf(
      IdentityUnavailableError,
    )
    expectSessionIntact()
  })

  it('leaves the session alone when the renewal itself fails', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(status(401)).mockResolvedValueOnce(status(500))
    vi.stubGlobal('fetch', fetchMock)

    await expect(identityRequest('/api/v1/auth/me')).rejects.toBeInstanceOf(
      IdentityUnavailableError,
    )
    expectSessionIntact()
  })

  it('leaves the session alone when there is no refresh token to renew with', async () => {
    saveSession({ accessToken: 'access-1', refreshToken: '' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(status(401)))

    await expect(identityRequest('/api/v1/auth/me')).rejects.toBeInstanceOf(
      IdentityUnavailableError,
    )
    expect(getAccessToken()).toBe('access-1')
  })

  it('reports one error type for every failure, saying nothing about the session', async () => {
    // The header must not draw a conclusion this error does not carry.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(status(503)))

    await expect(identityRequest('/api/v1/auth/me')).rejects.toThrow(
      'Данные учётной записи сейчас недоступны.',
    )
  })
})
