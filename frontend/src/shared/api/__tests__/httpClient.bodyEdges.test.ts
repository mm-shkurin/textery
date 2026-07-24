import { afterEach, describe, expect, it, vi } from 'vitest'
import { isHttpError, request } from '../httpClient'

afterEach(() => {
  vi.unstubAllGlobals()
})

// Two edges where the transport used to lie about what happened: a successful response with no
// body, and a Retry-After header that is not the delta-seconds the contract promises.
describe('httpClient response-body edges', () => {
  // A 204, or a 200 with an empty body, makes res.json() throw a bare SyntaxError. That is not an
  // HttpError, so it reaches the caller through the transport branch and renders as "check your
  // connection" — on a request that succeeded.
  it('treats an empty successful body as nothing to report, not as a network failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 204,
        headers: new Headers(),
        json: async () => {
          throw new SyntaxError('Unexpected end of JSON input')
        },
      }),
    )

    await expect(request('/api/v1/documents/doc-1')).resolves.toEqual({})
  })

  it('still rejects a non-ok response as an HttpError when its body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        headers: new Headers(),
        json: async () => {
          throw new SyntaxError('<html>')
        },
      }),
    )

    await expect(request('/api/v1/documents/doc-1')).rejects.toSatisfy(
      (error: unknown) => isHttpError(error) && error.status === 502,
    )
  })
})

describe('Retry-After parsing', () => {
  async function retryAfterFrom(headerValue: string): Promise<number | undefined> {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        headers: new Headers({ 'Retry-After': headerValue }),
        json: async () => ({}),
      }),
    )
    try {
      await request('/api/v1/auth/login')
      throw new Error('expected a rejection')
    } catch (error) {
      return isHttpError(error) ? error.retryAfterSeconds : undefined
    }
  }

  it('reads plain delta-seconds', async () => {
    await expect(retryAfterFrom('90')).resolves.toBe(90)
  })

  // `Number()` alone reads these as 16 and 1000 — a malformed header would put the account-locked
  // screen into a countdown the server never asked for. Absent is the honest answer.
  it.each(['0x10', '1e3', '  ', 'Wed, 21 Oct 2026 07:28:00 GMT', '-5', '12.5'])(
    'refuses %s rather than inventing a cooldown',
    async (value) => {
      await expect(retryAfterFrom(value)).resolves.toBeUndefined()
    },
  )
})
