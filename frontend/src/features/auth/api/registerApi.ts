// HTTP client for the registration API (POST create pending account).
//
// The wire contract here was verified by curl against the live backend on 2026-07-16, not
// read from `ProductSpecification/api-specs/` — the spec had drifted. Confirmed live:
//   201 → {user_id, is_verified, email, verification_code, code_expires_at}
//   409 → {error_code: "EMAIL_ALREADY_REGISTERED", message}
//   400 → {error_code: "INVALID_EMAIL"|"INVALID_PASSWORD"|"PASSWORD_MISMATCH", message}
//   422 → {detail: [...]} — Pydantic's envelope, emitted when a field is MISSING. It has no
//         `error_code`, so it lands on the generic fallback. That is correct: a 422 means
//         this client built a malformed body — a bug here, not something to explain to a user.
//
// `confirm_password` is REQUIRED by the backend. Omitting it was a real shipped bug:
// registration returned 422 and could never succeed, and no unit test caught it because
// they all mock this module.
import { postJson } from '../../../shared/api/httpClient'
import { toAuthApiError, type AuthApiError } from './apiError'
import { GENERIC_REGISTER_FAILURE_MESSAGE } from '../utils/authMessages'

export interface RegisterResult {
  userId: string
  email: string
  isVerified: boolean
  // The mocked verification code, returned in the register response because no email is
  // sent. It is the ONLY way to verify an account today — an intentional project trade-off
  // documented in 07_Authorization_Notes.md. Treat it as a credential: never log it.
  verificationCode: string
  codeExpiresAt: string
}

export type RegisterApiError = AuthApiError

// Registration has no code whose message the form supplies itself, so every code falls back to
// the one generic string. Unlike login, there is no branch here that must be told "the server
// said nothing" apart from "the server said it failed".
function toRegisterApiError(error: unknown): unknown {
  return toAuthApiError(error, () => GENERIC_REGISTER_FAILURE_MESSAGE)
}

export async function register(
  email: string,
  password: string,
  confirmPassword: string,
): Promise<RegisterResult> {
  try {
    const body = await postJson<Record<string, unknown>>('/api/v1/auth/register', {
      email,
      password,
      confirm_password: confirmPassword,
    })
    return {
      userId: String(body.user_id ?? ''),
      email: String(body.email ?? ''),
      isVerified: Boolean(body.is_verified),
      verificationCode: String(body.verification_code ?? ''),
      codeExpiresAt: String(body.code_expires_at ?? ''),
    }
  } catch (error) {
    throw toRegisterApiError(error)
  }
}
