// HTTP client for the registration API (POST create pending account).
import { postJson, type HttpError } from './httpClient'

export interface RegisterResult {
  email: string
}

export interface RegisterApiError {
  errorCode: string
  message: string
}

export async function register(email: string, password: string): Promise<RegisterResult> {
  try {
    return await postJson<RegisterResult>('/api/v1/auth/register', { email, password })
  } catch (error) {
    const httpError = error as HttpError
    const apiError: RegisterApiError = {
      errorCode: (httpError.body.error_code as string) ?? 'UNKNOWN_ERROR',
      message: (httpError.body.message as string) ?? 'Не удалось зарегистрироваться',
    }
    throw apiError
  }
}
