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

  // (i) Transport-failure survival. BORN GREEN — the body-existence guard at loginApi.ts:21 is
  // already implemented; this pins it against a revert to registerApi's naive
  // `(error as HttpError).body.error_code`, which would throw a SECOND TypeError from inside
  // the catch and lose the original. Identity (`toBe`) is what makes that distinction: a
  // re-thrown TypeError would satisfy `toBeInstanceOf(TypeError)` just as well.
  // MUTATION-VERIFIED (test-review): guard replaced by the naive `(error as HttpError).body`,
  // confirmed present (and the guard absent) by grep. Baseline 1F/5P → 2F/4P, new failure = this.
  it('rethrows a bodyless transport failure as the very error fetch rejected with', async () => {
    const transportError = new TypeError('Failed to fetch')
    stubFetchRejecting(transportError)

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toBe(transportError)
  })

  // (iii) Wire key mapping. BORN GREEN — a characterization pin, not a guard this step
  // established. The literal `body.error_code` at loginApi.ts:44 is asserted by nothing else in
  // the suite; this is the only test that goes red if the backend renames the field or wraps it
  // in an envelope. Body is the real wire shape from endpoints.md:17.
  // MUTATION-VERIFIED (test-review): `body.error_code` → `body.errorCode`, confirmed present by
  // grep. Baseline 1F/5P → 5F/1P; four are new (this, (ii)×2, (v)), the fifth is (iv), already
  // red at that baseline.
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
  // with a truthiness guard, deleting this step's only red before the step ran. A regression
  // pin, not presented as a guard this step established.
  //
  // MUTATION-VERIFIED (test-review) against the CURRENT line: `serverMessage || fallbackMessageFor`
  // → `??`, grep-confirmed present. Baseline 0F/7P → 2F/5P, killing BOTH cases below, nothing
  // else: `serverMessage` is normalized to `''` before the operator, so `??` never fires. The
  // prior record (a `message ?? GENERIC` line `9b556d9` DELETED, a dead 1F/5P baseline, "(iv)
  // flips GREEN") was RE-DERIVED not patched — it claimed 'message absent' survives. It does not.
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

  // (iv) THE RED THIS STEP ESTABLISHED — now FIXED. Read it as a regression pin, NOT as a
  // description of shipped code: the bug below is gone, and this comment is in the past tense
  // deliberately. `9b556d9` deleted it and renumbered; there is no "line 48 applies the
  // fallback under every code" any more (line 48 today is `errorCode,`).
  //
  // What it pinned: the PARENT commit applied the login-failure fallback under EVERY
  // error_code, and endpoints.md:17 makes {error_code, message} uniform across all codes. So
  // an UNVERIFIED error with a blank message was handed to the form as a login-failure display
  // constant the server never sent, provenance unrecoverable: 5.3's UNVERIFIED branch would
  // call isUsableMessage on the forged constant, get true, and render "sign-in failed" to a
  // user whose password was correct. `fallbackMessageFor` now scopes the fallback to the code
  // it describes, which is what keeps this test green.
  //
  // Asserted strictly rather than as a negative (`not.toBe(GENERIC)`), per test-review: the
  // negative admitted values that are not a decision at all (`undefined`, `null`, a `message`
  // field RENAMED out of existence all satisfy it), and "green decides" is the deferral the
  // No-Deferred-Assertions rule names outright — the test is the specification.
  //
  // `''` is not review inventing a fourth option — (v) pins that server text passes through
  // verbatim under a code the module does not special-case, and `''` is server text.
  // Downstream this is what 5.3 needs: `isUsableMessage('')` is false, so the form owns the
  // UNVERIFIED copy and no constant the server never sent reaches the screen.
  it('does not substitute the login-failure display constant under a non-login-failure code', async () => {
    stubFetchErrorBody(403, { error_code: 'UNVERIFIED', message: '' })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'UNVERIFIED', message: '' })
  })

  // (vii) THE `{}` BODY — the one error path that actually fires today, and the only one no
  // other fixture reaches. Of the six others, FIVE supply a well-formed `error_code`; (i)
  // supplies no body at all and is stopped by the `!body` rethrow guard before the normalizer
  // ever runs. This one supplies a body that is truthy but CODELESS: `postJson` does
  // `res.json().catch(() => ({}))` (httpClient.ts:19), so a 404 HTML page (no login endpoint
  // yet) or a proxy's 502 arrives as `{}` — truthy, so it clears the guard and is normalized.
  //
  // Added by green because green CHANGED this path and nothing here observed it. What it
  // uniquely pins is NARROW — MUTATION-VERIFIED against a 0F/7P baseline, both mutants
  // confirmed present by grep before running:
  //   * Mutation C, the trap SCOPED TO THE CODELESS BODY — return the raw HttpError when
  //     `body.error_code` is not a string = 1F/6P, killing THIS TEST ALONE. Its reason to exist.
  //   * Mutation B, the BROAD form — return the raw error whenever the code is
  //     non-INVALID_CREDENTIALS with no message = 2F/5P, killing (iv) AND this test. (iv)
  //     already catches that one; this test is not what stands between it and green.
  // An earlier revision justified the test by the BROAD form and claimed "the whole file would
  // stay green" without it. False — 2F/5P, as above. The correction was written into
  // progress.md the day the claim shipped, but the uncorrected claim was copied here in the
  // same commit; a future reader opens the test, not the progress file.
  //
  // Asserted below: still a LoginApiError, code `UNKNOWN_ERROR`, message `''` (no server text,
  // reported as absence). Not the login-failure constant — the code is not the login-failure
  // code. LoginForm supplies the generic copy via applyLoginError's fallback; screen unchanged.
  //
  // Stub shape follows generation/api/__tests__/generationApi.test.ts:41-54 — `json` throws
  // rather than resolving, as a non-JSON response really does. `stubFetchErrorBody` can't.
  it('normalizes an unparseable error body to UNKNOWN_ERROR with no server message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => {
          throw new SyntaxError('Unexpected token <')
        },
      }),
    )

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'UNKNOWN_ERROR', message: '' })
  })

  // (v) BORN GREEN — a characterization pin, not a guard this step established. It pins the
  // ACTUAL contract, which is not the one loginApi's comment claimed: the api preserves
  // whatever non-blank text the server sent, verbatim, including internal detail, and performs
  // no sanitisation. endpoints.md:17-19 puts client-safety on the BACKEND; non-disclosure on
  // the client lives solely in LoginForm's errorCode === 'INVALID_CREDENTIALS' check.
  // 5.3/5.4/5.6 will each add a consumer reading apiError.message; this test exists so none of
  // them can inherit the belief that the api layer already gated it.
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
