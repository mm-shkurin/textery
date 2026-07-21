// Login-rejection interpretation, split out of LoginForm so the component stays under the
// 200-line cap and the branching rules have one testable home. Each function reads a field off an
// `unknown` rejection and earns it with an `in`/typeof guard — nothing casts the error to a
// declared shape, because at run time nothing holds it to one (loginApi's return type says so).
import { GENERIC_LOGIN_FAILURE_MESSAGE, isUsableMessage } from './authMessages'
import { hasErrorCode, hasProp } from './errorGuards'

// UNVERIFIED is a DIFFERENT action for the user, not a reworded "sign-in failed": their password
// was right and they must go confirm the emailed code. Rendering the generic constant here told
// them the one thing that is not true. Confirmed live 2026-07-16: an unverified account gets
// 403 { error_code: "UNVERIFIED", message }.
export const UNVERIFIED_MESSAGE = 'Аккаунт не подтверждён. Введите код подтверждения из письма.'

export function isAccountLocked(error: unknown): boolean {
  return hasErrorCode(error, 'ACCOUNT_LOCKED')
}

// Is this rejection a network/transport failure rather than a business/validation response? Two
// shapes qualify, and merely-absent status is NOT one of them:
//   * TRANSPORT-SHAPED — the rejection is not an object carrying an `errorCode` (a bare
//     `TypeError('Failed to fetch')`, a bodyless connection drop). This is live regardless of
//     status, since a transport failure has no body to carry one.
//   * GATEWAY 5xx — a codeless `UNKNOWN_ERROR` body wearing a `status >= 500` (a proxy 502 during a
//     deploy). It is told from a GENUINE codeless business error ONLY by that 5xx status.
// Deliberately `status >= 500` only, never `status === undefined || status >= 500`: a status-less
// rejection that DOES carry an errorCode is a real client-side business error (production currently
// drops status), and must stay on the form-error path — routing it to "check your connection"
// would strand a 4xx behind the wrong message.
export function isLoginNetworkError(error: unknown): boolean {
  if (!hasProp(error, 'errorCode')) {
    return true
  }
  if (hasProp(error, 'status')) {
    return typeof error.status === 'number' && error.status >= 500
  }
  return false
}

// The cooldown the account-locked screen counts down. Sourced from the Retry-After header, which
// loginApi surfaces as `retryAfterSeconds` (deferred red-frontend-api). Returns NaN when the field
// is absent or not a number, so the screen falls back to its default window rather than rendering
// "NaN:NaN" — the field is best-effort, the lock is not.
export function readLockoutRetrySeconds(error: unknown): number {
  if (hasProp(error, 'retryAfterSeconds')) {
    const value = error.retryAfterSeconds
    return typeof value === 'number' ? value : NaN
  }
  return NaN
}

// The message the login form shows for a NON-lockout rejection. Lockout is handled separately (it
// swaps the whole screen, it is not a one-line message), so this function never sees it.
export function loginErrorMessage(error: unknown): string {
  if (hasErrorCode(error, 'UNVERIFIED')) {
    return UNVERIFIED_MESSAGE
  }
  if (
    hasErrorCode(error, 'INVALID_CREDENTIALS') &&
    hasProp(error, 'message') &&
    isUsableMessage(error.message)
  ) {
    return error.message
  }
  return GENERIC_LOGIN_FAILURE_MESSAGE
}
