// The registration form's position, as ONE value.
//
// Password and confirm validity are one state machine, not two independent fields: touching the
// password re-checks the confirm that was already typed. Holding the three complaints and the
// in-flight flag together is what lets a single named transition say that.
export interface RegisterSubmitState {
  isSubmitting: boolean
  emailError: string | null
  passwordError: boolean
  confirmError: boolean
}

export const INITIAL_REGISTER_STATE: RegisterSubmitState = {
  isSubmitting: false,
  emailError: null,
  passwordError: false,
  confirmError: false,
}

export type RegisterSubmitAction =
  | { type: 'submitStarted' }
  | { type: 'submitSettled' }
  | { type: 'accepted' }
  | { type: 'rejected'; message: string }
  // `confirmError` is absent while the confirm field has never been blurred: a password blur must
  // not light up a mismatch against a field the user has not reached yet.
  | { type: 'passwordBlurred'; passwordError: boolean; confirmError?: boolean }
  | { type: 'confirmBlurred'; confirmError: boolean }

export function registerSubmitReducer(
  state: RegisterSubmitState,
  action: RegisterSubmitAction,
): RegisterSubmitState {
  switch (action.type) {
    case 'submitStarted':
      return { ...state, isSubmitting: true }
    case 'submitSettled':
      return { ...state, isSubmitting: false }
    case 'accepted':
      return { ...state, emailError: null }
    case 'rejected':
      return { ...state, emailError: action.message }
    case 'passwordBlurred':
      return {
        ...state,
        passwordError: action.passwordError,
        confirmError: action.confirmError ?? state.confirmError,
      }
    case 'confirmBlurred':
      return { ...state, confirmError: action.confirmError }
  }
}
