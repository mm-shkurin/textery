import { afterEach, describe, expect, it, vi } from 'vitest'
import { resendCode } from '../authApi'

// The resend-code client, whose two failure arms are the whole of it.
//
// It had no test. The module is exercised only through VerifyCodeForm, which mocks it, so the one
// distinction it exists to make - a server that refused versus a request that never reached one -
// was asserted nowhere. That distinction is not cosmetic: it is what the previous version got
// wrong. `error as HttpError` satisfied the compiler and lied at run time, so an offline user was
// told "HTTP undefined" - a status invented for a request no server ever saw.
//
// The success arm is pinned to the WIRE shape the backend actually answers with. It used to be
// `{code}`, which the client passed straight through, so the test agreed with the client about a
// field neither of them had ever seen: the route answers `verification_code`. Both were wrong
// together, which is why the suite stayed green while the one field that makes this call useful
// read `undefined` — and a user who pressed «Отправить снова» went on being shown the retired
// code, could never verify, and met 403 UNVERIFIED at the login screen.
const WIRE_SUCCESS = { verification_code: '123456', code_expires_at: '2026-08-14T10:00:00+00:00' }

function stubFetch(response: unknown) {
  const mock = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', mock)
  return mock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('resendCode', () => {
  it('posts the email and returns the issued code', async () => {
    const fetchMock = stubFetch({ ok: true, status: 200, json: async () => WIRE_SUCCESS })

    const result = await resendCode('user@example.com')

    // The client's own shape, mapped from the wire — not a pass-through of the response.
    expect(result).toEqual({ code: '123456' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/auth/resend-code')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ email: 'user@example.com' })
  })

  it('names the status when a server refused the request', async () => {
    stubFetch({ ok: false, status: 429, json: async () => ({}) })

    // The status is in the message because it is the only fact a user can pass on: 429 and 500
    // mean "wait" and "it broke", and a support conversation that starts with the number gets to
    // the answer without a log dive. This is the arm where a status genuinely exists.
    await expect(resendCode('user@example.com')).rejects.toThrow(
      'Не удалось отправить код повторно (HTTP 429)',
    )
  })

  it('does not invent a status when the request never reached a server', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const failure = await resendCode('user@example.com').catch((error: unknown) => error)

    // The exact bug this narrowing was added for: a transport rejection carries no `status`, and
    // reading one off it produced «(HTTP undefined)» on an offline screen - a phantom response
    // from a server that was never contacted. Asserted as an exact message rather than a
    // `not.toContain('undefined')`, which would also pass on text this module never writes.
    expect(failure).toEqual(new Error('Не удалось отправить код повторно'))
  })
})
