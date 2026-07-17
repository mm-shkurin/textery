import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { authorizedRequest, SessionExpiredError } from '../authorizedRequest'
import { clearSession, getAccessToken, getRefreshToken, saveSession } from '../../utils/authSession'

// fetch is stubbed rather than the refresh client mocked: the refresh round-trip IS the subject
// here, and mocking it would leave the one thing that replaces tokens untested.
function okOnce(body: unknown) {
  return { ok: true, status: 200, json: async () => body }
}

function unauthorized() {
  return {
    ok: false,
    status: 401,
    json: async () => ({ error_code: 'INVALID_ACCESS_TOKEN', message: 'expired' }),
  }
}

// Matches the live backend's /auth/refresh 200 (probed 2026-07-17): a new refresh token comes
// back alongside the new access token, carrying an expiry 7 days from now.
function refreshedTokens(suffix: string) {
  return okOnce({
    access_token: `access-${suffix}`,
    refresh_token: `refresh-${suffix}`,
    access_token_expires_at: '2026-07-17T00:15:00Z',
    refresh_token_expires_at: '2026-07-24T00:00:00Z',
  })
}

function isRefreshCall(call: unknown[]): boolean {
  return String(call[0]).includes('/auth/refresh')
}

describe('authorizedRequest', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('attaches the access token as a Bearer header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okOnce({ fine: true }))
    vi.stubGlobal('fetch', fetchMock)

    await authorizedRequest('/api/v1/generations/gen-1')

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer access-1')
  })

  it('refuses to call the API at all when there is no session', async () => {
    clearSession()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    await expect(authorizedRequest('/api/v1/generations')).rejects.toBeInstanceOf(
      SessionExpiredError,
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })

  // The headline behaviour: an access token expires roughly every 15 minutes, and the user must
  // never see that happen.
  it('renews the session and replays the request on 401', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(unauthorized())
      .mockResolvedValueOnce(refreshedTokens('2'))
      .mockResolvedValueOnce(okOnce({ generation_id: 'gen-1' }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await authorizedRequest<{ generation_id: string }>('/api/v1/generations', {
      method: 'POST',
      body: { topic: 'Тема' },
    })

    expect(result).toEqual({ generation_id: 'gen-1' })
    expect(fetchMock.mock.calls[1][0]).toContain('/api/v1/auth/refresh')
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer access-2')
  })

  // Both halves, not just the access token. Each refresh issues a refresh token expiring 7 days
  // from now, so storing it slides the window; dropping it caps every session at 7 days from
  // first login and then ends it mid-use. That bug is a week away from its cause, which is
  // exactly why it needs a test rather than a reviewer.
  it('persists the new refresh token, not just the new access token', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(unauthorized())
        .mockResolvedValueOnce(refreshedTokens('2'))
        .mockResolvedValueOnce(okOnce({})),
    )

    await authorizedRequest('/api/v1/generations/gen-1')

    expect(getAccessToken()).toBe('access-2')
    expect(getRefreshToken()).toBe('refresh-2')
  })

  it('replays a POST with its original Idempotency-Key so the retry is not a second request', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(unauthorized())
      .mockResolvedValueOnce(refreshedTokens('2'))
      .mockResolvedValueOnce(okOnce({}))
    vi.stubGlobal('fetch', fetchMock)

    await authorizedRequest('/api/v1/generations', {
      method: 'POST',
      headers: { 'Idempotency-Key': 'key-1' },
      body: { topic: 'Тема' },
    })

    expect(fetchMock.mock.calls[2][1].headers['Idempotency-Key']).toBe('key-1')
  })

  // Polling makes overlapping requests the normal case, so one expiry lands on several at once.
  // Without single-flight each fires its own refresh and the last to finish decides which token
  // is stored, overwriting tokens the others are mid-use with — and N pollers become N auth
  // calls.
  it('refreshes once for concurrent 401s', async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => {
      if (String(url).includes('/auth/refresh')) return refreshedTokens('2')
      return okOnce({ ok: true })
    })
    // Both original calls 401 before either refresh completes.
    fetchMock.mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(unauthorized())
    vi.stubGlobal('fetch', fetchMock)

    await Promise.all([
      authorizedRequest('/api/v1/generations/a'),
      authorizedRequest('/api/v1/generations/b'),
    ])

    expect(fetchMock.mock.calls.filter(isRefreshCall)).toHaveLength(1)
  })

  // Keeping tokens we could not renew defers the same dead end to the next request — by which
  // point the user has typed something they are about to lose. End it here, and let the UI's
  // session subscription collapse the screen.
  it('clears the session and reports expiry when the refresh token is rejected', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(unauthorized())
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: async () => ({ error_code: 'INVALID_REFRESH_TOKEN', message: 'expired' }),
        }),
    )

    await expect(authorizedRequest('/api/v1/generations/gen-1')).rejects.toBeInstanceOf(
      SessionExpiredError,
    )
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  // A 401 on a brand-new token is not staleness and will not become staleness. Retrying it is
  // how a client hammers an endpoint until the account locks.
  it('does not retry more than once', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(unauthorized())
      .mockResolvedValueOnce(refreshedTokens('2'))
      .mockResolvedValueOnce(unauthorized())
    vi.stubGlobal('fetch', fetchMock)

    await expect(authorizedRequest('/api/v1/generations/gen-1')).rejects.toMatchObject({
      status: 401,
    })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('passes a non-401 failure through untouched, without refreshing', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'boom' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(authorizedRequest('/api/v1/generations/gen-1')).rejects.toMatchObject({
      status: 500,
    })
    expect(fetchMock.mock.calls.filter(isRefreshCall)).toHaveLength(0)
  })
})
