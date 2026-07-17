// HTTP client for the login API (POST authenticate).
import { postJson } from '../../../shared/api/httpClient'
import { toAuthApiError, type AuthApiError } from './apiError'
import { GENERIC_LOGIN_FAILURE_MESSAGE } from '../utils/authMessages'

// The wire is snake_case — verified by curl against the live backend 2026-07-16:
//   200 → {access_token, refresh_token, access_token_expires_at, refresh_token_expires_at}
// This interface previously declared camelCase and nothing mapped to it, so every field was
// silently `undefined`. It never surfaced because LoginForm discarded the result entirely and
// every component test mocks this module. The mapping below is the boundary; the rest of the
// app sees camelCase.
export interface LoginResult {
  accessToken: string
  refreshToken: string
  accessTokenExpiresAt: string
  refreshTokenExpiresAt: string
}

export type LoginApiError = AuthApiError

// The body-shape rule (rethrow bodyless transport failures, guard each field on its own terms)
// is `toAuthApiError`'s and shared with register/verify. What is specific to login is the
// fallback below — so that is all this module passes in.
//
// NOTE on what does NOT happen here: this module performs NO sanitisation. Any non-whitespace
// string passes through verbatim, `"NullPointerException at AuthService.line42"` included.
// Client-safety is the BACKEND's guarantee (endpoints.md:17-19 — `message` is always a generic,
// client-safe string). On this side, non-disclosure is enforced SOLELY by LoginForm's
// `errorCode === 'INVALID_CREDENTIALS'` check, which decides what reaches the screen. Consumers
// added later (5.3/5.4/5.6 each read `apiError.message`) must gate the text themselves: it does
// not arrive display-ready, whatever its type says.
function toLoginApiError(error: unknown): unknown {
  return toAuthApiError(error, fallbackMessageFor)
}

// What this module may put in `message` when the server sent no usable text.
//
// GENERIC_LOGIN_FAILURE_MESSAGE is a DISPLAY constant owned by this client and specific to
// ONE meaning: "sign-in failed". Stamping it onto an error whose code means something else
// forges provenance that cannot be recovered downstream — a consumer reading such a message
// through `isUsableMessage` sees a usable server string and renders login-failure copy for a
// user whose password was right (exactly the trap 5.3's UNVERIFIED branch would fall into).
// So the fallback is scoped to the code it describes; under every other code the absence of
// server text is reported AS absence, `''`.
//
// `''` rather than omitting the field: `isUsableMessage('')` is false, so each consumer's
// own guard fires and the form owns the copy for that code — which is what 5.3/5.4/5.6 need.
// Keeping the field present also keeps `LoginApiError` one shape, so the `''` is a value the
// type describes rather than a hole the type lies about.
//
// This is also the answer for the `{}` body: a proxy's 502 or any non-JSON error page makes
// `res.json()` throw and `postJson` substitutes `{}` (shared/api/httpClient.ts). That body is truthy,
// so it clears the
// rethrow guard above and lands here with no `error_code` → `UNKNOWN_ERROR` + `''`. It stays
// a LoginApiError: returning the raw HttpError instead would hand the form a `{status, body}`
// no consumer reads. Only the codeless-body trap escapes the other fixtures — the broad form
// ("return raw for any non-INVALID_CREDENTIALS code") is already caught by the UNVERIFIED
// test. LoginForm's non-INVALID_CREDENTIALS path renders the generic constant
// for it, so the screen is unchanged — the constant is now applied by the layer that OWNS
// display, not forged by the layer that reports the wire.
function fallbackMessageFor(errorCode: string): string {
  return errorCode === 'INVALID_CREDENTIALS' ? GENERIC_LOGIN_FAILURE_MESSAGE : ''
}

export async function login(email: string, password: string): Promise<LoginResult> {
  try {
    const body = await postJson<Record<string, unknown>>('/api/v1/auth/login', { email, password })
    return {
      accessToken: String(body.access_token ?? ''),
      refreshToken: String(body.refresh_token ?? ''),
      accessTokenExpiresAt: String(body.access_token_expires_at ?? ''),
      refreshTokenExpiresAt: String(body.refresh_token_expires_at ?? ''),
    }
  } catch (error) {
    throw toLoginApiError(error)
  }
}
