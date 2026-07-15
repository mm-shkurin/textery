// HTTP client for the auth resend-code endpoint.
import { postJson, type HttpError } from './httpClient'

export interface ResendCodeResult {
  code: string
}

export async function resendCode(email: string): Promise<ResendCodeResult> {
  try {
    return await postJson<ResendCodeResult>('/api/v1/auth/resend-code', { email })
  } catch (error) {
    const httpError = error as HttpError
    throw new Error(`Не удалось отправить код повторно (HTTP ${httpError.status})`)
  }
}
