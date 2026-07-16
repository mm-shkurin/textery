// HTTP client for the login API (POST authenticate).
import { postJson, type HttpError } from './httpClient'
import { GENERIC_LOGIN_FAILURE_MESSAGE } from '../utils/loginMessages'

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
  // Truthiness, not `??`: `??` fires only on null/undefined, so an empty-string message
  // would survive verbatim and reach the form as '' — falsy at the form's render guard,
  // i.e. silence on the INVALID_CREDENTIALS path itself.
  const message = body.message
  const apiError: LoginApiError = {
    errorCode: (body.error_code as string) || 'UNKNOWN_ERROR',
    message: typeof message === 'string' && message ? message : GENERIC_LOGIN_FAILURE_MESSAGE,
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
