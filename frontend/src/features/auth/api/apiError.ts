// The one place that turns an auth endpoint's error body into the {errorCode, message} pair the
// forms match on. register/verify/login each carried a verbatim copy of this rule; they differed
// only in which constant filled a missing message, which is a parameter, not a reason to fork.
import { type HttpError } from '../../../shared/api/httpClient'
import { isUsableMessage } from '../utils/authMessages'

// Every auth client's error shape. The forms compare `errorCode` against the codes they know and
// decide for themselves whether `message` may reach the screen — it does NOT arrive display-ready.
export interface AuthApiError {
  errorCode: string
  message: string
  // Carried through from the response's Retry-After header (httpClient) when present. Shared by
  // every auth client, but today only login's account-locked screen reads it; a register/verify
  // 429 would surface it too, harmlessly (no consumer there). Absent when no header — never NaN.
  retryAfterSeconds?: number
  // The transport's HTTP status, attached ONLY on the codeless (UNKNOWN_ERROR) path — a body with
  // no usable `error_code`. A coded error is already told apart by its `errorCode`, so it keeps its
  // two-field shape (the coded-error toStrictEqual tests are the guard forcing this to be
  // conditional). This is the wire discriminator green-frontend's `status>=500` branch reads to
  // tell a 5xx gateway/transport failure from a codeless business error; it carries no display copy.
  status?: number
}

// The code stamped on a body that carried no usable `error_code`: a 422 from Pydantic, or a
// proxy's non-JSON 502 (which `postJson` substitutes `{}` for). It matches no known code, so the
// caller's own fallback fires — the correct outcome, since those bodies describe a bug on this
// side rather than something to explain to a user.
export const UNKNOWN_ERROR_CODE = 'UNKNOWN_ERROR'

// Map a rejection to an AuthApiError, or return it untouched when it is not one.
//
// A rejection only carries a body when `postJson` built an HttpError from a non-ok response.
// Transport failures (fetch rejects with a bodyless TypeError) have no body — they are rethrown
// as-is rather than having `.body` read off `undefined`, so no internal error text reaches a form.
//
// `fallbackMessageFor` belongs to the caller: it decides what a missing message means under each
// code, so the module that owns the copy keeps the decision.
export function toAuthApiError(
  error: unknown,
  fallbackMessageFor: (errorCode: string) => string,
): unknown {
  const body = (error as HttpError | undefined)?.body
  if (!body || typeof body !== 'object') {
    return error
  }
  // The two guards are NOT the same rule and must not be collapsed — what disqualifies a value
  // differs by what the value is for. `errorCode` is only ever compared, never shown, so any
  // non-empty string serves. `message` is displayed, so a blank string must lose to the fallback;
  // `??` would fire only on null/undefined and let `''` through, leaving the form silent.
  const rawCode = body.error_code
  const hasUsableCode = typeof rawCode === 'string' && rawCode
  const errorCode = hasUsableCode ? rawCode : UNKNOWN_ERROR_CODE
  const serverMessage = isUsableMessage(body.message) ? body.message : ''
  const apiError: AuthApiError = {
    errorCode,
    message: serverMessage || fallbackMessageFor(errorCode),
  }
  // Codeless-path-only status pass-through: on the UNKNOWN_ERROR path the body carried no
  // discriminator of its own, so preserve the transport status (read off HttpError just as `.body`
  // is above) — this is the ONLY bit that lets green-frontend tell a 5xx gateway failure from a
  // codeless business error. NOT attached on the coded path: a coded error is distinguished by its
  // errorCode and must keep its exact two-field shape (coded-error toStrictEqual tests are the
  // guard). Finite-guard mirrors retryAfterSeconds below: only a real numeric status is attached.
  if (!hasUsableCode) {
    const status = (error as HttpError | undefined)?.status
    if (typeof status === 'number' && Number.isFinite(status)) {
      apiError.status = status
    }
  }
  // Header-driven pass-through: attach only when httpClient parsed a finite Retry-After, so the key
  // is present for a lockout/429 and absent otherwise. Guards NaN out — httpClient never sets it to
  // NaN, and this re-checks finiteness so a hand-built HttpError can't smuggle one in.
  const retryAfterSeconds = (error as HttpError | undefined)?.retryAfterSeconds
  if (typeof retryAfterSeconds === 'number' && Number.isFinite(retryAfterSeconds)) {
    apiError.retryAfterSeconds = retryAfterSeconds
  }
  return apiError
}
