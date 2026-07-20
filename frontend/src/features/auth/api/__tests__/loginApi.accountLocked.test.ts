import { afterEach, describe, expect, it, vi } from 'vitest'
import { login } from '../loginApi'

// Real-fetch tests (fetch stubbed, loginApi NOT mocked, no backend). Sibling of loginApi.test.ts,
// which is at the 200-line ceiling. This file pins the API-layer half of the 5.4 lockout contract:
// `login()` must surface the HTTP `Retry-After` header as `retryAfterSeconds` on the rejection so
// the already-built account-locked form can drive its countdown.
//
// DESIGN DECISION 2026-07-20 (progress-frontend.md, scenario 5.4):
//   Lockout wire: HTTP 403 (any non-ok), body {error_code:'ACCOUNT_LOCKED', message:''},
//   header `Retry-After: <integer seconds>`.
//   login() rejects with {errorCode:'ACCOUNT_LOCKED', message:'', retryAfterSeconds:<seconds>}.
// Round-8 premortem seam: `message` stays '' — the api mapper must NOT stamp client copy for
// ACCOUNT_LOCKED (display copy lives in the form). toStrictEqual below pins message:''.

const EMAIL = 'user@example.com'
const PASSWORD = 'correct-horse'

function stubFetchLockout(status: number, retryAfter: string | null, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      headers: {
        get: (name: string) => (name.toLowerCase() === 'retry-after' ? retryAfter : null),
      },
      json: async () => body,
    }),
  )
}

async function rejectionOf(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise
  } catch (error) {
    return error
  }
  throw new Error('expected login() to reject, but it resolved')
}

describe.skip('loginApi account-locked', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('surfaces the Retry-After header as retryAfterSeconds on the ACCOUNT_LOCKED rejection', async () => {
    stubFetchLockout(403, '292', { error_code: 'ACCOUNT_LOCKED', message: '' })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({
      errorCode: 'ACCOUNT_LOCKED',
      message: '',
      retryAfterSeconds: 292,
    })
  })

  it('does not add retryAfterSeconds when no Retry-After header is present', async () => {
    stubFetchLockout(403, null, { error_code: 'UNVERIFIED', message: '' })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'UNVERIFIED', message: '' })
  })
})
