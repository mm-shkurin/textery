// HTTP client for the account-verification API (POST confirm the mocked code).
//
// Contract verified by curl against the live backend on 2026-07-16, not from the spec:
//   200 → {is_verified: true}   — IDEMPOTENT: replaying the same code returns 200 again,
//                                 so a double submit is not an error path.
//   400 → {error_code: "INVALID_CODE", message}            — code is not 6 ASCII digits
//   400 → {error_code: "INVALID_OR_EXPIRED_CODE", message} — wrong / expired / no such
//                                                            account / no code issued.
//         The backend deliberately collapses those four causes into one code; do not try
//         to tell them apart here, and do not surface a distinction the server refused to
//         make — that would be the account-enumeration oracle this story exists to avoid.
//   500 → {detail: "internal server error"} — no `error_code`, lands on the fallback.
import { postJson } from '../../../shared/api/httpClient'
import { toAuthApiError, type AuthApiError } from './apiError'
import { GENERIC_VERIFY_FAILURE_MESSAGE } from '../utils/authMessages'

export interface VerifyResult {
  isVerified: boolean
}

export type VerifyApiError = AuthApiError

function toVerifyApiError(error: unknown): unknown {
  return toAuthApiError(error, () => GENERIC_VERIFY_FAILURE_MESSAGE)
}

export async function verify(email: string, code: string): Promise<VerifyResult> {
  try {
    const body = await postJson<Record<string, unknown>>('/api/v1/auth/verify', { email, code })
    return { isVerified: Boolean(body.is_verified) }
  } catch (error) {
    throw toVerifyApiError(error)
  }
}
