// Verify-rejection interpretation, split out of VerifyCodeForm so the component stays under the
// 200-line cap and the branching rules have one testable home — mirrors loginErrorHandling. Each
// reader takes an `unknown` rejection and earns the field with an `in`/typeof guard; nothing casts
// the error to a declared shape, because at run time nothing holds it to one (verifyApi's return
// type says so).
import { GENERIC_VERIFY_FAILURE_MESSAGE, isUsableMessage } from './authMessages'
import { hasErrorCode, hasProp } from './errorGuards'

// The distinct wrong-code copy the FORM owns, keyed off errorCode — NEVER a server-relayed string.
// The api mapper leaves `message: ''` for these codes (round-8 display seam), so this copy can only
// come from here, exactly as login's UNVERIFIED_MESSAGE is substituted for the UNVERIFIED code.
export const WRONG_CODE_MESSAGE = 'Неверный или устаревший код. Проверьте его и попробуйте снова.'

// Both rejection codes mean the same thing to the user — "the code you submitted is not acceptable,
// check it and try again" — so both render one message. INVALID_OR_EXPIRED_CODE is the backend's
// deliberate collapse of wrong/expired/no-account/no-code into one code (the enumeration oracle this
// story exists to avoid); INVALID_CODE is malformed input (not 6 ASCII digits). Neither gives the
// user a different action, so the client does NOT surface a distinction they cannot act on, and does
// NOT try to tell apart causes the backend already collapsed.
function isWrongCode(error: unknown): boolean {
  return hasErrorCode(error, 'INVALID_OR_EXPIRED_CODE') || hasErrorCode(error, 'INVALID_CODE')
}

// The message the verify form shows for a rejection. A wrong-code rejection gets the form-owned
// copy; any other coded rejection relays a usable server message; everything else falls back.
export function verifyErrorMessage(error: unknown): string {
  if (isWrongCode(error)) {
    return WRONG_CODE_MESSAGE
  }
  if (hasProp(error, 'errorCode') && hasProp(error, 'message') && isUsableMessage(error.message)) {
    return error.message
  }
  return GENERIC_VERIFY_FAILURE_MESSAGE
}
