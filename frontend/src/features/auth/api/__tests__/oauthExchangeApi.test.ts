import { afterEach, describe, expect, it, vi } from 'vitest'
import { oauthExchange } from '../oauthExchangeApi'
import { rejectionOf } from './loginApiTestUtils'

// Real-fetch tests: `fetch` is stubbed, `oauthExchange` is NOT mocked. This is the only place the
// exchange client's wire boundary is executed — snake_case → camelCase (sessionTokensFromWire) and
// the shared toAuthApiError seam — the same layer/quality as loginApi.test.ts.
//
// BORN GREEN: green-frontend 3.1 already shipped the real mapping (postJson + sessionTokensFromWire
// + toAuthApiError). No RED is recoverable against the current impl; these pin the wire contract of
// POST /api/v1/auth/oauth/exchange against a revert (a forked/renamed field, a dropped error seam).

const HANDOFF_CODE = 'handoff-code-xyz'

function stubFetchOk(status: number, body: unknown): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status,
    json: async () => body,
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function stubFetchErrorBody(status: number, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: async () => body,
    }),
  )
}

describe('oauthExchange', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Request contract: POSTs the handoff code to the exchange endpoint with an exact { code } body.
  it('POSTs { code } to /api/v1/auth/oauth/exchange', async () => {
    const fetchMock = stubFetchOk(200, {
      access_token: 'a',
      refresh_token: 'r',
      access_token_expires_at: 'ax',
      refresh_token_expires_at: 'rx',
    })

    await oauthExchange({ code: HANDOFF_CODE })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/auth/oauth/exchange')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toStrictEqual({ code: HANDOFF_CODE })
  })

  // Success mapping: the snake_case 200 body maps to the exact 4-field camelCase OAuthSession — the
  // snake→camel boundary now shared through sessionTokensFromWire, pinned whole in one place.
  it('maps the snake_case 200 body onto the camelCase OAuthSession', async () => {
    stubFetchOk(200, {
      access_token: 'access-123',
      refresh_token: 'refresh-456',
      access_token_expires_at: '2026-07-22T10:00:00Z',
      refresh_token_expires_at: '2026-07-29T10:00:00Z',
    })

    const session = await oauthExchange({ code: HANDOFF_CODE })

    expect(session).toStrictEqual({
      accessToken: 'access-123',
      refreshToken: 'refresh-456',
      accessTokenExpiresAt: '2026-07-22T10:00:00Z',
      refreshTokenExpiresAt: '2026-07-29T10:00:00Z',
    })
  })

  // Error mapping: a coded error is rejected through the shared toAuthApiError seam, surfacing the
  // two-field { errorCode, message } shape (mirrors loginApi's coded-error assertion).
  it('maps a coded error body onto errorCode and a verbatim message', async () => {
    stubFetchErrorBody(400, {
      error_code: 'INVALID_OR_EXPIRED_OAUTH_CODE',
      message: 'Код входа истёк',
    })

    const rejection = await rejectionOf(oauthExchange({ code: HANDOFF_CODE }))

    expect(rejection).toStrictEqual({
      errorCode: 'INVALID_OR_EXPIRED_OAUTH_CODE',
      message: 'Код входа истёк',
    })
  })
})
