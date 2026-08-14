// HTTP client for the auth resend-code endpoint.
//
// THE ENDPOINT EXISTS. The note that stood here said it was absent and answered 404 (checked
// 2026-07-17); `POST /api/v1/auth/resend-code` has since shipped and answers 200 with a NEW code,
// or 429 RESEND_COOLDOWN_ACTIVE while the previous one is still fresh. The stale note mattered:
// while it stood, nobody looked at what the route returns.
//
// It returns `verification_code`, not `code`. The interface below claimed the latter, so the one
// field that makes this call worth anything read `undefined` — and no test caught it, because no
// caller read the result at all.
import { postJson, isHttpError } from '../../../shared/api/httpClient'

const RESEND_FAILURE_MESSAGE = 'Не удалось отправить код повторно'

export interface ResendCodeResult {
  code: string
}

interface ResendCodeWire {
  verification_code?: unknown
}

export async function resendCode(email: string): Promise<ResendCodeResult> {
  try {
    const body = await postJson<ResendCodeWire>('/api/v1/auth/resend-code', { email })
    const code = body.verification_code
    return { code: typeof code === 'string' ? code : '' }
  } catch (error) {
    // Narrow before reading `.status`. The previous `error as HttpError` cast satisfied the
    // compiler and lied at run time: a transport failure rejects with a bodyless TypeError, so
    // an offline user was told "HTTP undefined" — a phantom status for a request that never
    // reached a server. Only a real non-ok response has a status worth naming.
    if (isHttpError(error)) {
      throw new Error(`${RESEND_FAILURE_MESSAGE} (HTTP ${error.status})`)
    }
    throw new Error(RESEND_FAILURE_MESSAGE)
  }
}
