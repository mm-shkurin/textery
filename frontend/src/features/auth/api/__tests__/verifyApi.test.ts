import { afterEach, describe, expect, it, vi } from 'vitest'
import { verify } from '../verifyApi'
import { GENERIC_VERIFY_FAILURE_MESSAGE } from '../../utils/authMessages'

// verifyApi sat at 0% statements: all six VerifyCodeForm tests mock the module, so the request
// it actually sends and the error shape it actually raises were executed by nothing — the same
// blind spot historyApi had. Mocking a module everywhere makes its callers testable and its own
// contract untested; these tests close that for the verify endpoint.
describe('verifyApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function stubFetch(response: Record<string, unknown>): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn().mockResolvedValue({
      headers: { get: () => null },
      ...response,
    })
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  it('posts the email and code to the verify endpoint as JSON', async () => {
    const fetchMock = stubFetch({
      ok: true,
      status: 200,
      json: async () => ({ is_verified: true }),
    })

    await verify('user@example.com', '123456')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/auth/verify')
    expect(init.method).toBe('POST')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body)).toEqual({ email: 'user@example.com', code: '123456' })
  })

  it('reads the verified flag off the wire body', async () => {
    stubFetch({ ok: true, status: 200, json: async () => ({ is_verified: true }) })

    await expect(verify('user@example.com', '123456')).resolves.toEqual({ isVerified: true })
  })

  // Boolean(), not a pass-through: an absent flag must read as "not verified" rather than as
  // undefined, which every caller would treat as falsy anyway but which types as a boolean here.
  it.each([
    ['an absent flag', {}],
    ['an explicit false', { is_verified: false }],
    ['a null flag', { is_verified: null }],
  ])('reports not-verified for %s', async (_label, body) => {
    stubFetch({ ok: true, status: 200, json: async () => body })

    await expect(verify('user@example.com', '123456')).resolves.toEqual({ isVerified: false })
  })

  // The backend collapses wrong / expired / no-such-account / no-code-issued into ONE code on
  // purpose — the anti-enumeration decision. The client must carry the code through untouched
  // rather than re-deriving a distinction the server refused to make.
  it.each(['INVALID_CODE', 'INVALID_OR_EXPIRED_CODE'])(
    'surfaces the %s rejection with its error code intact',
    async (errorCode) => {
      stubFetch({
        ok: false,
        status: 400,
        json: async () => ({ error_code: errorCode, message: 'нельзя' }),
      })

      await expect(verify('user@example.com', '000000')).rejects.toMatchObject({ errorCode })
    },
  )

  // A 500 answers with FastAPI's `detail` and no error_code, so there is nothing to key copy off
  // — it must land on the generic line rather than rendering an internal message to the user.
  it('falls back to the generic failure message for an uncoded server error', async () => {
    stubFetch({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'internal server error' }),
    })

    await expect(verify('user@example.com', '123456')).rejects.toMatchObject({
      message: GENERIC_VERIFY_FAILURE_MESSAGE,
    })
  })

  // A transport failure is not an HTTP response: it carries no status and no body, and must stay
  // distinguishable from a rejection so the form offers a retry instead of a field error.
  it('propagates a transport failure rather than dressing it as a coded rejection', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(verify('user@example.com', '123456')).rejects.toThrow('Failed to fetch')
  })
})
