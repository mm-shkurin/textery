// Login-rejection interpretation, split out of LoginForm so the component stays under the
// 200-line cap and the branching rules have one testable home. Each function reads a field off an
// `unknown` rejection and earns it with an `in`/typeof guard — nothing casts the error to a
// declared shape, because at run time nothing holds it to one (loginApi's return type says so).
import { GENERIC_LOGIN_FAILURE_MESSAGE, isUsableMessage } from './authMessages'

// UNVERIFIED is a DIFFERENT action for the user, not a reworded "sign-in failed": their password
// was right and they must go confirm the emailed code. Rendering the generic constant here told
// them the one thing that is not true. Confirmed live 2026-07-16: an unverified account gets
// 403 { error_code: "UNVERIFIED", message }.
export const UNVERIFIED_MESSAGE = 'Аккаунт не подтверждён. Введите код подтверждения из письма.'

export function hasErrorCode(error: unknown, code: string): boolean {
  return (
    Boolean(error) &&
    typeof error === 'object' &&
    error !== null &&
    'errorCode' in error &&
    error.errorCode === code
  )
}

export function isAccountLocked(error: unknown): boolean {
  return hasErrorCode(error, 'ACCOUNT_LOCKED')
}

// The cooldown the account-locked screen counts down. Sourced from the Retry-After header, which
// loginApi surfaces as `retryAfterSeconds` (deferred red-frontend-api). Returns NaN when the field
// is absent or not a number, so the screen falls back to its default window rather than rendering
// "NaN:NaN" — the field is best-effort, the lock is not.
export function readLockoutRetrySeconds(error: unknown): number {
  if (error && typeof error === 'object' && 'retryAfterSeconds' in error) {
    const value = (error as { retryAfterSeconds: unknown }).retryAfterSeconds
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
    error &&
    typeof error === 'object' &&
    'message' in error &&
    isUsableMessage(error.message)
  ) {
    return error.message
  }
  return GENERIC_LOGIN_FAILURE_MESSAGE
}
