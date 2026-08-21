// The login screen's position, as ONE value.
//
// The four outcomes of a submit are genuinely different states, not one message with different
// text: a lockout swaps the screen, a transport failure gets its own retry-capable banner, a
// rejected credential gets the field-level message, and success navigates. Held as four
// independent switches they could be combined into screens the product does not have — a lockout
// with a field error under it, a network banner left over from the previous attempt.
export interface LoginSubmitState {
  isSubmitting: boolean
  formError: string | null
  // A network/transport failure is a DIFFERENT state from a rejected credential: it renders its
  // own retry-capable element, visually distinct from the field-level validation error, so the
  // user is told the connection dropped rather than that their password was wrong.
  networkError: boolean
  // Non-null once the server reports a lockout: the seconds it wants us to wait. Its presence,
  // not a message, is what swaps the whole screen for the account-locked one.
  lockoutSeconds: number | null
}

export const INITIAL_LOGIN_STATE: LoginSubmitState = {
  isSubmitting: false,
  formError: null,
  networkError: false,
  lockoutSeconds: null,
}

// Named for what happened, not for what each one assigns.
export type LoginSubmitAction =
  | { type: 'submitStarted' }
  | { type: 'submitSettled' }
  | { type: 'lockedOut'; seconds: number | null }
  | { type: 'connectionFailed' }
  | { type: 'rejected'; message: string }
  | { type: 'lockoutDismissed' }

export function loginSubmitReducer(
  state: LoginSubmitState,
  action: LoginSubmitAction,
): LoginSubmitState {
  switch (action.type) {
    // The previous attempt's complaints go with it. The lockout does NOT: it is a fact about the
    // account that a new submit cannot clear, and only the countdown or the user leaving does.
    case 'submitStarted':
      return { ...state, isSubmitting: true, formError: null, networkError: false }
    case 'submitSettled':
      return { ...state, isSubmitting: false }
    case 'lockedOut':
      return { ...state, lockoutSeconds: action.seconds }
    case 'connectionFailed':
      return { ...state, networkError: true }
    case 'rejected':
      return { ...state, formError: action.message }
    case 'lockoutDismissed':
      return { ...state, lockoutSeconds: null }
  }
}
