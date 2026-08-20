// The one definition of how many boxes the code has stays with the markup that draws them
// (VerifyCodeInputs); the state that fills them reads it from there rather than keeping a second
// copy that could drift.
import { CODE_LENGTH } from '../components/VerifyCodeInputs'

export const RESEND_FAILURE_MESSAGE = 'Не удалось отправить код повторно. Попробуйте ещё раз позже.'
export const MISSING_EMAIL_MESSAGE =
  'Не найден email для подтверждения — начните регистрацию заново'

// The verify screen's position, as ONE value.
//
// Seven independent switches is how this screen was written, and the combinations they allow are
// the bugs it has had: a retired code still displayed next to fresh boxes, a red code field over a
// success message, «Отправить снова» disabled by a submit that had nothing to do with it. Every
// transition below writes several of them at once, which is the honest description.
export interface VerifyCodeState {
  // STATE, not a read of the router: a resend ISSUES A NEW CODE and retires the one on screen.
  // Held as a constant, the screen went on showing the retired code after «Отправить снова», the
  // user typed what they were shown, the server refused it, and the account stayed unverified —
  // which is answered by 403 UNVERIFIED at the login screen, i.e. "I registered and now I cannot
  // sign in".
  mockedCode: string | undefined
  digits: string[]
  codeError: boolean
  formError: string | null
  isVerified: boolean
  isSubmitting: boolean
  isResending: boolean
}

export function initialVerifyState(mockedCode: string | undefined): VerifyCodeState {
  return {
    mockedCode,
    digits: Array(CODE_LENGTH).fill(''),
    codeError: false,
    formError: null,
    isVerified: false,
    isSubmitting: false,
    isResending: false,
  }
}

export type VerifyCodeAction =
  | { type: 'digitsChanged'; digits: string[] }
  | { type: 'emailMissing' }
  | { type: 'submitStarted' }
  | { type: 'submitSettled' }
  | { type: 'verified' }
  | { type: 'refused'; message: string }
  | { type: 'resendStarted' }
  | { type: 'resendSettled' }
  | { type: 'codeReissued'; code: string }
  | { type: 'resendFailed' }

export function verifyCodeReducer(
  state: VerifyCodeState,
  action: VerifyCodeAction,
): VerifyCodeState {
  switch (action.type) {
    // Editing the code clears the error paint — the boxes no longer show the value the server
    // rejected, so keeping them red would accuse input the user has already changed.
    case 'digitsChanged':
      return { ...state, digits: action.digits, codeError: false }
    case 'emailMissing':
      return { ...state, formError: MISSING_EMAIL_MESSAGE }
    case 'submitStarted':
      return { ...state, isSubmitting: true }
    case 'submitSettled':
      return { ...state, isSubmitting: false }
    case 'verified':
      return { ...state, isVerified: true, formError: null, codeError: false }
    // Both a rejection and a 200 that says `is_verified: false`. The backend has never sent the
    // latter, but the field only means something if we read it — treating any 200 as "verified"
    // would make the flag decoration.
    case 'refused':
      return { ...state, isVerified: false, formError: action.message, codeError: true }
    case 'resendStarted':
      return { ...state, isResending: true, formError: null }
    case 'resendSettled':
      return { ...state, isResending: false }
    // The new code REPLACES the one on screen, and the boxes are emptied with it. Discarding it
    // left the retired code displayed, and since no mail is sent, the displayed code is the only
    // one the user has.
    case 'codeReissued':
      return {
        ...state,
        mockedCode: action.code,
        digits: Array(CODE_LENGTH).fill(''),
        codeError: false,
      }
    // Swallowing this made the button a no-op that LOOKS like it worked: the user waits for a code
    // that was never issued, and blames the mail that never arrives. The status code stays out of
    // the copy on purpose — an HTTP number is a fact about our deployment, not one the user can
    // act on.
    case 'resendFailed':
      return { ...state, formError: RESEND_FAILURE_MESSAGE }
  }
}
