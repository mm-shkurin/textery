import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { register, type RegisterApiError } from '../api/registerApi'
import { rememberRegistration } from '../utils/registrationHandoff'
import {
  UNSAVED_LEAVE_MESSAGE_REGISTER,
  useUnsavedGuard,
} from '../../../shared/hooks/useUnsavedGuard'
import { GENERIC_REGISTER_FAILURE_MESSAGE, isUsableMessage } from '../utils/authMessages'
import { isConfirmMismatched, isPasswordCompliant } from '../utils/passwordPolicy'

// 'EMAIL_ALREADY_REGISTERED' is what the backend actually sends on 409 — confirmed by curl
// against the live stack on 2026-07-16. This branch previously matched 'EMAIL_ALREADY_EXISTS',
// a code the backend never emits, so the duplicate-email message could never render. Every
// unit test passed throughout, because they all mock registerApi and assert against the
// invented code.
const DUPLICATE_EMAIL_ERROR_CODE = 'EMAIL_ALREADY_REGISTERED'

// Every rejection resolves to user-facing text — silence is an illegal terminal state, the rule
// LoginForm already states and this form was missing. It returned `null` for anything but a
// duplicate email, and the caller's `if (message)` then set nothing: a 500, a dropped connection
// or an INVALID_PASSWORD left the button springing back with no explanation at all, which reads
// as "the click did nothing" and earns a second identical submit.
//
// The duplicate-email message is the server's own (the backend's `message` guarantee covers it,
// and it is the one code whose text is worth quoting). Every other code — including a body that
// arrived without one — falls back to the client-owned generic constant rather than to nothing.
function applyRegisterError(error: unknown): string {
  if (error && typeof error === 'object' && 'errorCode' in error) {
    const apiError = error as RegisterApiError
    if (apiError.errorCode === DUPLICATE_EMAIL_ERROR_CODE && isUsableMessage(apiError.message)) {
      return apiError.message
    }
  }
  return GENERIC_REGISTER_FAILURE_MESSAGE
}

// The registration screen's whole submit-and-validate lifecycle, extracted for the reason
// useLoginSubmit already was: the component is then markup plus a state read, and its two
// sibling forms are shaped alike rather than one being a hook and the other 194 lines of both.
// The blur handlers live here too — password and confirm validity are one state machine, not
// two independent fields: touching the password re-checks the confirm that was already typed.
export function useRegisterSubmit() {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [emailError, setEmailError] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState(false)
  const [confirmError, setConfirmError] = useState(false)
  // Whether the confirm field has ever been blurred. Until it has, a password blur must not
  // light up a mismatch against a field the user has not reached yet.
  const confirmTouchedRef = useRef(false)
  const { markDirty, markClean, confirmLeave } = useUnsavedGuard(UNSAVED_LEAVE_MESSAGE_REGISTER)
  const emailInputRef = useRef<HTMLInputElement>(null)
  const passwordInputRef = useRef<HTMLInputElement>(null)
  const confirmInputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    setIsSubmitting(true)
    const password = passwordInputRef.current?.value ?? ''
    try {
      const result = await register(
        emailInputRef.current?.value ?? '',
        password,
        confirmInputRef.current?.value ?? '',
      )
      setEmailError(null)
      // The input has been sent — it is no longer unsaved, so release the guard BEFORE the
      // navigation below. A failed submit skips this (we never reach here on throw), keeping
      // the still-unsaved data guarded — scenario 5.8 case 4.
      markClean()
      // Hand the password to /verify so a verified account lands signed in. In memory only, and
      // deliberately NOT in the router state below — see registrationHandoff for why that
      // distinction is the whole point.
      rememberRegistration(result.email, password)
      // The mocked code is carried in router state, not the URL: a query string would land
      // in browser history and server logs, and the notes require treating it as a real
      // credential. `replace` keeps Back from returning to a form whose submit already
      // consumed the email.
      navigate('/verify', {
        replace: true,
        state: { email: result.email, verificationCode: result.verificationCode },
      })
    } catch (error) {
      setEmailError(applyRegisterError(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  function handlePasswordBlur(event: React.FocusEvent<HTMLInputElement>) {
    const password = event.target.value
    setPasswordError(password.length > 0 && !isPasswordCompliant(password))

    if (confirmTouchedRef.current) {
      setConfirmError(isConfirmMismatched(password, confirmInputRef.current?.value ?? ''))
    }
  }

  function handleConfirmBlur(event: React.FocusEvent<HTMLInputElement>) {
    confirmTouchedRef.current = true
    setConfirmError(isConfirmMismatched(passwordInputRef.current?.value ?? '', event.target.value))
  }

  // In-app react-router navigation does not raise `beforeunload`, so guard the footer login
  // link at its own click seam: cancel the navigation unless the form is pristine or the user
  // confirms leaving.
  function handleLeaveClick(event: React.MouseEvent<HTMLAnchorElement>) {
    if (!confirmLeave()) {
      event.preventDefault()
    }
  }

  return {
    emailInputRef,
    passwordInputRef,
    confirmInputRef,
    isSubmitting,
    emailError,
    passwordError,
    confirmError,
    markDirty,
    handleSubmit,
    handlePasswordBlur,
    handleConfirmBlur,
    handleLeaveClick,
  }
}
