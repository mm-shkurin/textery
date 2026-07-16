import { afterEach, describe, expect, it, vi } from 'vitest'
import { login } from '../loginApi'
import { GENERIC_LOGIN_FAILURE_MESSAGE } from '../../utils/loginMessages'

// Real-fetch tests: `fetch` is stubbed, `loginApi` is NOT mocked. Every LoginForm test file
// does `vi.mock('../../api/loginApi')`, so `toLoginApiError` and `postJson` are unreachable
// from the component layer — this file is the only place their behavior is executed.

const EMAIL = 'user@example.com'
const PASSWORD = 'correct-horse'

function stubFetchRejecting(error: unknown): void {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
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

async function rejectionOf(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise
  } catch (error) {
    return error
  }
  throw new Error('expected login() to reject, but it resolved')
}

describe('loginApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // (i) Transport-failure survival. BORN GREEN — the body-existence guard at loginApi.ts:21
  // is already implemented; this pins it against a revert to registerApi's naive
  // `(error as HttpError).body.error_code`, which would throw a SECOND TypeError from inside
  // the catch and lose the original. Identity (`toBe`) is what makes that distinction:
  // a re-thrown TypeError would satisfy `toBeInstanceOf(TypeError)` just as well.
  // MUTATION-VERIFIED (test-review): guard replaced by the naive `(error as HttpError).body`,
  // mutation confirmed present (and the guard confirmed absent) by grep before running.
  // Baseline 1F/5P → 2F/4P; the one new failure is this test.
  it('rethrows a bodyless transport failure as the very error fetch rejected with', async () => {
    const transportError = new TypeError('Failed to fetch')
    stubFetchRejecting(transportError)

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toBe(transportError)
  })

  // (iii) Wire key mapping. BORN GREEN — a characterization pin, not a guard this step
  // established. The literal `body.error_code` at loginApi.ts:44 is asserted by nothing else
  // in the suite; this is the only test that goes red if the backend renames the field or
  // wraps it in an envelope. Body is the real wire shape from endpoints.md:17.
  // MUTATION-VERIFIED (test-review): `body.error_code` → `body.errorCode`, mutation confirmed
  // present in the file by grep before running. Baseline 1F/5P → 5F/1P. Four of those five
  // are new (this test, (ii)×2, (v)); the fifth is (iv), already red at baseline.
  it('maps the wire error_code/message body onto errorCode and a verbatim message', async () => {
    stubFetchErrorBody(401, {
      error_code: 'INVALID_CREDENTIALS',
      message: 'Неверный email или пароль',
    })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({
      errorCode: 'INVALID_CREDENTIALS',
      message: 'Неверный email или пароль',
    })
  })

  // (ii) Message fallback on the INVALID_CREDENTIALS path. BORN GREEN, AND NO RED IS
  // RECOVERABLE: this would have failed before commit e98b3d1, which replaced `?? GENERIC`
  // with a truthiness guard and thereby deleted this step's only red before the step ran.
  // Kept as a regression pin, not presented as a guard this step established.
  //
  // MUTATION-VERIFIED (test-review): the fallback reverted to `message ?? GENERIC`, mutation
  // confirmed present by grep before running. Baseline 1F/5P → 1F/5P — the SAME COUNT, and
  // a count-only reading would call this mutant survived. It is not: the failing test CHANGES
  // identity. 'message empty' goes red (`'' ?? GENERIC` → `''`, no fallback), while (iv) flips
  // GREEN (`''` is not the GENERIC constant, so (iv)'s negative is satisfied). Compare tests,
  // never totals. 'message absent' does NOT die under this mutant — `undefined ?? GENERIC`
  // still yields GENERIC — so it is 'message empty' alone that pins the `??` regression.
  //
  // The pair is also what scopes (iv): (ii) demands GENERIC under INVALID_CREDENTIALS + '',
  // (iv) forbids GENERIC under UNVERIFIED + ''. Together they force green to make the
  // login-failure fallback conditional on the login-failure code — neither does it alone.
  it.each([
    ['message absent', { error_code: 'INVALID_CREDENTIALS' }],
    ['message empty', { error_code: 'INVALID_CREDENTIALS', message: '' }],
  ])(
    'falls back to the generic login-failure message when %s',
    async (_case, body) => {
      stubFetchErrorBody(401, body)

      const rejection = await rejectionOf(login(EMAIL, PASSWORD))

      expect(rejection).toStrictEqual({
        errorCode: 'INVALID_CREDENTIALS',
        message: GENERIC_LOGIN_FAILURE_MESSAGE,
      })
    },
  )

  // (iv) THE RED. loginApi.ts:48 applies the login-failure fallback under EVERY error_code,
  // not only INVALID_CREDENTIALS, and endpoints.md:17 makes {error_code, message} uniform
  // across all codes. So an UNVERIFIED error with a blank message is handed to the form as a
  // login-failure display constant the server never sent, with provenance unrecoverable:
  // 5.3's UNVERIFIED branch calls isUsableMessage on the forged constant, gets true, and
  // renders "sign-in failed" to a user whose password was correct.
  //
  // Was asserted as a negative (`not.toBe(GENERIC)`) on the grounds that what the api emits
  // instead — an absent message, a per-code constant, or no display copy with the form owning
  // all of it — is green's decision. test-review made it strict, for two reasons.
  //
  // 1. The negative admitted values that are not a decision at all. `not.toBe` is satisfied by
  //    `undefined`, `null`, and by a `message` field RENAMED out of existence — the unchecked
  //    cast `(rejection as { message: unknown }).message` reads `undefined` and passes green
  //    while the field it guards no longer exists.
  // 2. "Green decides" is the deferral the No-Deferred-Assertions rule names outright. The
  //    test is the specification; the value gets decided here, and green matches it.
  //
  // `''` is not review inventing a fourth option — it is the third of the listed three, and
  // it is the one the file's other pins ALREADY entail. (v) pins that server text passes
  // through verbatim under a code the module does not special-case; `''` is server text, so
  // verbatim of `''` is `''`. The rule this test asks green for is therefore not new
  // behaviour, it is the REMOVAL of a special case: the login-failure fallback stops firing
  // under codes that are not the login-failure code. Downstream this is exactly what 5.3
  // needs — `isUsableMessage('')` is false, so the form owns the UNVERIFIED copy and no
  // constant the server never sent reaches the screen. If green prefers "message absent", it
  // must change (v) too, and that is the argument this strict form forces into the open.
  it('does not substitute the login-failure display constant under a non-login-failure code', async () => {
    stubFetchErrorBody(403, { error_code: 'UNVERIFIED', message: '' })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'UNVERIFIED', message: '' })
  })

  // (v) BORN GREEN — a characterization pin, not a guard this step established. It pins the
  // ACTUAL contract, which is not the one loginApi's comment claimed: the api
  // preserves whatever non-blank text the server sent, verbatim, including internal detail.
  // It performs no sanitisation. endpoints.md:17-19 puts client-safety on the BACKEND, and
  // non-disclosure on the client lives solely in LoginForm's errorCode === 'INVALID_CREDENTIALS'
  // check. 5.3/5.4/5.6 will each add a consumer reading apiError.message; this test exists so
  // none of them can inherit the belief that the api layer already gated it.
  it('preserves server text verbatim under an unrecognised code, performing no sanitisation', async () => {
    const internalText = 'NullPointerException at AuthService.line42'
    stubFetchErrorBody(500, { error_code: 'INTERNAL_SERVER_ERROR', message: internalText })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({
      errorCode: 'INTERNAL_SERVER_ERROR',
      message: internalText,
    })
  })
})
