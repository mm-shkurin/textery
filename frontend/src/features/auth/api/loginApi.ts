// HTTP client for the login API (POST authenticate).
import { postJson, type HttpError } from './httpClient'

export interface LoginResult {
  accessToken: string
  refreshToken: string
}

export interface LoginApiError {
  errorCode: string
  message: string
}

const GENERIC_LOGIN_FAILURE_MESSAGE = 'Не удалось войти'

// A rejection only carries an error body when postJson built an HttpError from a
// non-ok response. Transport failures (fetch rejects with a bodyless TypeError)
// have no body — rethrow them untouched rather than reading `.body` off undefined,
// so no internal error text can reach the login screen.
function toLoginApiError(error: unknown): unknown {
  const body = (error as HttpError | undefined)?.body
  if (!body || typeof body !== 'object') {
    return error
  }
  const apiError: LoginApiError = {
    errorCode: (body.error_code as string) ?? 'UNKNOWN_ERROR',
    message: (body.message as string) ?? GENERIC_LOGIN_FAILURE_MESSAGE,
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
