// HTTP client for the login API (POST authenticate).
import { postJson, type HttpError } from './httpClient'
import { GENERIC_LOGIN_FAILURE_MESSAGE, isUsableMessage } from '../utils/loginMessages'

export interface LoginResult {
  accessToken: string
  refreshToken: string
}

export interface LoginApiError {
  errorCode: string
  message: string
}

// A rejection only carries an error body when postJson built an HttpError from a
// non-ok response. Transport failures (fetch rejects with a bodyless TypeError)
// have no body — rethrow them untouched rather than reading `.body` off undefined,
// so no internal error text can reach the login screen.
function toLoginApiError(error: unknown): unknown {
  const body = (error as HttpError | undefined)?.body
  if (!body || typeof body !== 'object') {
    return error
  }
  // Both fields fall back when the parsed value cannot serve, but the two tests are NOT the
  // same rule and must not be collapsed into one — what disqualifies a value differs by what
  // the value is for. `message` is rendered to the user, so it must carry visible text:
  // `isUsableMessage`, shared with LoginForm precisely so this module and the form cannot
  // hold two different notions of "displayable". `errorCode` is only ever compared against
  // known codes, never shown, so a non-empty string is enough; a blank-looking code is not
  // a display hazard, it simply matches nothing and lands on the form's own fallback.
  //
  // `??` is wrong for either field — it fires only on null/undefined, so an empty-string
  // message would survive verbatim and reach the form as '', silence on the
  // INVALID_CREDENTIALS path itself. `as string` is wrong in the other direction: `body` is
  // parsed JSON, so a non-string value satisfies the cast at compile time and lies about
  // the field at run time. Both guards earn the declared type instead of asserting it.
  const errorCode = body.error_code
  const message = body.message
  const apiError: LoginApiError = {
    errorCode: typeof errorCode === 'string' && errorCode ? errorCode : 'UNKNOWN_ERROR',
    message: isUsableMessage(message) ? message : GENERIC_LOGIN_FAILURE_MESSAGE,
  }
  return apiError
}

export async function login(email: string, password: string): Promise<LoginResult> {
  try {
    return await postJson<LoginResult>('/api/v1/auth/login', { email, password })
  } catch (error) {
    throw toLoginApiError(error)
  }
}
