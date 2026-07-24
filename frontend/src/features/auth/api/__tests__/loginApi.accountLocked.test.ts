import { afterEach, describe, expect, it, vi } from 'vitest'
import { login } from '../loginApi'
import { EMAIL, PASSWORD, rejectionOf } from './loginApiTestUtils'

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

describe('loginApi account-locked', () => {
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

  // Header-driven, NOT code-driven (agent-review/premortem on the red commit): a green that keyed
  // attachment on errorCode==='ACCOUNT_LOCKED' would pass the first test yet DROP a Retry-After on
  // a 429 rate-limit (a non-lockout code). This pins attachment to the header's presence, and the
  // 60 (≠ the other test's 292) forces a real string→number parse rather than a hardcoded constant.
  it('surfaces Retry-After for a NON-lockout code too (attachment is header-driven)', async () => {
    stubFetchLockout(429, '60', { error_code: 'RATE_LIMITED', message: '' })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({
      errorCode: 'RATE_LIMITED',
      message: '',
      retryAfterSeconds: 60,
    })
  })

  // The converse: ACCOUNT_LOCKED WITHOUT a header must NOT gain the key (a code-driven green would
  // wrongly attach it, likely as NaN). Proves omission is driven by header-absence, not the code.
  it('omits retryAfterSeconds for ACCOUNT_LOCKED when the header is absent', async () => {
    stubFetchLockout(403, null, { error_code: 'ACCOUNT_LOCKED', message: '' })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'ACCOUNT_LOCKED', message: '' })
  })

  // Retry-After may be an HTTP-date (RFC 9110), not delta-seconds — or garbage from a proxy.
  // parseInt/Number would yield NaN; the api must OMIT the key rather than attach NaN (a value the
  // `number` type permits and downstream readers without the form's triple-defense would trust).
  it('omits retryAfterSeconds when Retry-After is a non-numeric (HTTP-date) value, never NaN', async () => {
    stubFetchLockout(403, 'Wed, 21 Oct 2026 07:28:00 GMT', {
      error_code: 'ACCOUNT_LOCKED',
      message: '',
    })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'ACCOUNT_LOCKED', message: '' })
  })
})
