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
import { postJson, type HttpError } from '../../../shared/api/httpClient'

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

export interface RegisterApiError {
  errorCode: string
  message: string
}

const GENERIC_REGISTER_FAILURE_MESSAGE = 'Не удалось зарегистрироваться'

function toRegisterApiError(error: unknown): unknown {
  const body = (error as HttpError | undefined)?.body
  if (!body || typeof body !== 'object') {
    return error
  }
  const errorCode = body.error_code
  const message = body.message
  const apiError: RegisterApiError = {
    errorCode: typeof errorCode === 'string' && errorCode ? errorCode : 'UNKNOWN_ERROR',
    message:
      typeof message === 'string' && message.trim() ? message : GENERIC_REGISTER_FAILURE_MESSAGE,
  }
  return apiError
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
