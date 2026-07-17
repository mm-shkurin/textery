// HTTP client for the auth resend-code endpoint.
//
// THE ENDPOINT DOES NOT EXIST YET. `POST /api/v1/auth/resend-code` is specified in
// `ProductSpecification/stories/07-authorization/endpoints.md` and is absent from the running
// backend — its OpenAPI document lists register/verify/login/refresh only, and a call returns
// 404 (verified 2026-07-17). So every `resendCode` below rejects, by deployment rather than by
// bug. This client is correct and stays; the caller now surfaces the failure instead of
// swallowing it, so the gap is visible on screen until the backend ships the route.
import { postJson, type HttpError } from '../../../shared/api/httpClient'

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
