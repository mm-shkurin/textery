import { afterEach, describe, expect, it, vi } from 'vitest'
import { login } from '../loginApi'

// Real-fetch tests (fetch stubbed, loginApi NOT mocked, no backend). Third sibling of
// loginApi.test.ts (at the 200-line ceiling) and loginApi.accountLocked.test.ts. This file pins
// the API-layer half of scenario 5.6's CREDIBLE-1: when the wire carries NO usable error_code, the
// HTTP status must SURVIVE normalization onto AuthApiError so a 5xx gateway/transport failure is
// distinguishable from a codeless business error. Without it both collapse to
// {errorCode:'UNKNOWN_ERROR', message:''} and green-frontend's `status>=500` network branch is
// INERT in production — it never fires because the discriminator was thrown away one layer down.
//
// SCOPE: status is preserved ONLY on the codeless (UNKNOWN_ERROR) path. A coded error is already
// told apart by its errorCode, so it keeps its two-field shape — pinned by loginApi.test.ts's
// coded-error toStrictEqual tests, which must stay green. Those existing tests ARE the guard that
// forces the attach to be conditional; green cannot thread status onto every error without
// breaking them, and green-agent is tests-read-only.

const EMAIL = 'user@example.com'
const PASSWORD = 'correct-horse'

function stubFetchUnparseable(status: number): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: async () => {
        throw new SyntaxError('Unexpected token <')
      },
    }),
  )
}

function stubFetchCodelessBody(status: number, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status,
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

// RED (5.6 red-frontend-api): skipped until green-frontend-api threads `status` through
// HttpError → toAuthApiError → AuthApiError. Un-skip at green, same convention as scenario 5.6's
// LoginForm.networkError.test.tsx (describe.skip during red, un-skipped at green-frontend).
describe.skip('loginApi transport status', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // A proxy's 502 with an HTML (non-JSON) body: `postJson` substitutes `{}`, so the code falls back
  // to UNKNOWN_ERROR. The status must survive so green-frontend's `status>=500` branch can fire.
  it('preserves the 5xx status on an unparseable-body rejection so a gateway failure is identifiable', async () => {
    stubFetchUnparseable(502)

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'UNKNOWN_ERROR', message: '', status: 502 })
  })

  // The distinguishability contract: a codeless business error (4xx) and a codeless gateway failure
  // (5xx) would BOTH be {errorCode:'UNKNOWN_ERROR', message:''} without status. With status
  // preserved, the two are distinct values (400 vs 502) and green-frontend's branch fires on the
  // gateway one alone. Pinning status:400 here proves status is not special-cased to 5xx at the api
  // layer — the mapper preserves whatever the transport knew; the 5xx decision lives in the form.
  it('preserves a 4xx status on a codeless body, keeping it distinguishable from a 5xx failure', async () => {
    stubFetchCodelessBody(400, {})

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'UNKNOWN_ERROR', message: '', status: 400 })
  })
})
