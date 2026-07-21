import { afterEach, describe, expect, it, vi } from 'vitest'
import { login } from '../loginApi'
import { GENERIC_LOGIN_FAILURE_MESSAGE } from '../../utils/authMessages'
import { EMAIL, PASSWORD, rejectionOf } from './loginApiTestUtils'

// Real-fetch tests: `fetch` is stubbed, `loginApi` is NOT mocked. Every LoginForm test file
// does `vi.mock('../../api/loginApi')`, so `toLoginApiError` and `postJson` are unreachable
// from the component layer — this file is the only place their behavior is executed.

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

describe('loginApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // (i) Transport-failure survival. BORN GREEN — the body-existence guard at loginApi.ts:21 is
  // already implemented; this pins it against a revert to registerApi's naive
  // `(error as HttpError).body.error_code`, which would throw a SECOND TypeError from inside
  // the catch and lose the original. Identity (`toBe`) is what makes that distinction: a
  // re-thrown TypeError would satisfy `toBeInstanceOf(TypeError)` just as well.
  // MUTATION-VERIFIED, re-derived against the MEASURED 0F/7P baseline (the prior record cited
  // 1F/5P → 2F/4P; that baseline totals six and this file has SEVEN tests, so it was dead, and
  // its 2F/4P did not survive re-running either). Guard replaced by the naive
  // `(error as HttpError).body`, mutant grep-confirmed present and the guard confirmed gone:
  // 0F/7P → 1F/6P, killing THIS TEST ALONE. Its reason to exist.
  it('rethrows a bodyless transport failure as the very error fetch rejected with', async () => {
    const transportError = new TypeError('Failed to fetch')
    stubFetchRejecting(transportError)

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toBe(transportError)
  })

  // (iii) Wire key mapping. BORN GREEN — a characterization pin, not a guard this step
  // established. It states the whole mapping in one place: the wire body from endpoints.md:17
  // in, both fields out. ("The only test that goes red if the backend renames the field" was
  // the prior claim here; the mutation below measures FIVE, so it is deleted rather than
  // softened.)
  // MUTATION-VERIFIED, re-derived against the MEASURED 0F/7P baseline (the prior record cited
  // 1F/5P → 5F/1P; both total six, this file has SEVEN tests). `body.error_code` →
  // `body.errorCode`, mutant grep-confirmed present and the original confirmed gone: 0F/7P →
  // **5F/2P**, killing (ii)×2, (iii), (iv), (v); (i) and (vii) survive. All five are NEW kills:
  // the prior record called (iv) "already red at that baseline", which is false — (iv) is green
  // today (that was 5.2's whole point), so nothing here is red before the mutation.
  //
  // Note what that makes this test: NOT the sole guard on the wire key. Four other tests fail
  // alongside it, so the field rename it advertises catching is over-determined; the mutant
  // that isolates it has not been found. Kept as the characterization pin its name claims.
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
  // RECOVERABLE: commit e98b3d1 replaced `?? GENERIC` with a truthiness guard, deleting this
  // step's only red before the step ran. A regression pin, not a guard this step established.
  //
  // MUTATION-VERIFIED against the CURRENT line: `serverMessage || fallbackMessageFor` → `??`,
  // grep-confirmed present. 0F/7P → 2F/5P, killing BOTH cases below and nothing else:
  // `serverMessage` is normalized to `''` first, so `??` never fires. (The prior record cited a
  // line `9b556d9` DELETED and a dead 1F/5P baseline; re-derived, not patched.)
  //
  // The pair also scopes (iv): (ii) demands GENERIC under INVALID_CREDENTIALS + '', (iv)
  // forbids it under UNVERIFIED + ''. Together they force the fallback to be conditional on
  // the login-failure code — neither does it alone.
  it.each([
    ['message absent', { error_code: 'INVALID_CREDENTIALS' }],
    ['message empty', { error_code: 'INVALID_CREDENTIALS', message: '' }],
  ])('falls back to the generic login-failure message when %s', async (_case, body) => {
    stubFetchErrorBody(401, body)

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({
      errorCode: 'INVALID_CREDENTIALS',
      message: GENERIC_LOGIN_FAILURE_MESSAGE,
    })
  })

  // (iv) THE RED THIS STEP ESTABLISHED — now FIXED. A regression pin, NOT a description of
  // shipped code: `9b556d9` deleted the bug and renumbered (line 48 today is `errorCode,`).
  //
  // What it pinned: the PARENT commit applied the login-failure fallback under EVERY
  // error_code, and endpoints.md:17 makes {error_code, message} uniform across all codes. So an
  // UNVERIFIED error with a blank message reached the form as a login-failure constant the
  // server never sent, provenance unrecoverable: 5.3's UNVERIFIED branch would call
  // isUsableMessage on the forged constant, get true, and render "sign-in failed" to a user
  // whose password was correct. `fallbackMessageFor` now scopes the fallback to the code it
  // describes, which keeps this test green.
  //
  // Asserted strictly, not as `not.toBe(GENERIC)`: the negative admits values that are not a
  // decision at all (`undefined`, `null`, a renamed field), and "green decides" is the deferral
  // the No-Deferred-Assertions rule names — the test is the specification. `''` is server text,
  // per (v); downstream `isUsableMessage('')` is false, so 5.3's form owns the UNVERIFIED copy.
  it('does not substitute the login-failure display constant under a non-login-failure code', async () => {
    stubFetchErrorBody(403, { error_code: 'UNVERIFIED', message: '' })

    const rejection = await rejectionOf(login(EMAIL, PASSWORD))

    expect(rejection).toStrictEqual({ errorCode: 'UNVERIFIED', message: '' })
  })

  // (vii) THE `{}` / UNPARSEABLE BODY — relocated and UPGRADED to loginApi.transportStatus.test.ts
  // by 5.6's red-frontend-api. It previously asserted `toStrictEqual({errorCode:'UNKNOWN_ERROR',
  // message:''})`, which PINNED THE STATUS-LOSS this scenario fixes: the mapper drops the HTTP
  // status, so a 502 gateway failure and a codeless business error collapse to one value and
  // green-frontend's `status>=500` network branch is inert in production. The sibling now pins the
  // opposite — status SURVIVES onto the codeless AuthApiError — so keeping this test here would
  // contradict the new contract. Moving it also keeps this file under the 200-line cap.

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
