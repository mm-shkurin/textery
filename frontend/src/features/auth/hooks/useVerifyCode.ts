import { useReducer } from 'react'
import { useNavigate } from 'react-router-dom'
import { resendCode } from '../api/authApi'
import { verify } from '../api/verifyApi'
import { useResendCountdown } from './useResendCountdown'
import { signInAfterVerification } from '../utils/postVerifySignIn'
import { GENERIC_VERIFY_FAILURE_MESSAGE } from '../utils/authMessages'
import { verifyErrorMessage } from '../utils/verifyErrorHandling'
import { initialVerifyState, verifyCodeReducer } from '../utils/verifyCodeState'

// The verify screen's whole lifecycle — the code on display, the six boxes, the confirm and the
// resend — extracted for the reason useLoginSubmit and useRegisterSubmit already were: the
// component is then markup plus a state read. The position itself is one value moved by named
// transitions; see verifyCodeState.
//
// Rejection interpretation (wrong-code distinct message, usable-server-message pass-through,
// generic fallback) lives in ../utils/verifyErrorHandling, mirroring login's loginErrorHandling.
export function useVerifyCode(email: string | undefined, initialCode: string | undefined) {
  const navigate = useNavigate()
  const countdown = useResendCountdown()
  const [state, dispatch] = useReducer(verifyCodeReducer, initialCode, initialVerifyState)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (state.isSubmitting) return
    if (!email) {
      dispatch({ type: 'emailMissing' })
      return
    }
    dispatch({ type: 'submitStarted' })
    try {
      const result = await verify(email, state.digits.join(''))
      if (!result.isVerified) {
        dispatch({ type: 'refused', message: GENERIC_VERIFY_FAILURE_MESSAGE })
        return
      }
      dispatch({ type: 'verified' })
      // Verification does not mint a session, so getting into the app is a separate step that
      // can land in two places. Whatever it decides, the user leaves this screen: staying put
      // after a successful confirm is what made this form look hung.
      navigate(await signInAfterVerification(email), { replace: true })
    } catch (error) {
      dispatch({ type: 'refused', message: verifyErrorMessage(error) })
    } finally {
      dispatch({ type: 'submitSettled' })
    }
  }

  async function handleResend() {
    if (!email || !countdown.isElapsed) return
    dispatch({ type: 'resendStarted' })
    try {
      const result = await resendCode(email)
      if (result.code) dispatch({ type: 'codeReissued', code: result.code })
      // Only a resend that actually happened restarts the wait. Restarting on a failure would
      // lock the user out of retrying for a minute over a request the server never accepted.
      countdown.restart()
    } catch {
      // The route ships now and answers 200 or 429 RESEND_COOLDOWN_ACTIVE, so this branch is a
      // real failure again rather than the permanent 404 the note here used to describe.
      dispatch({ type: 'resendFailed' })
    } finally {
      dispatch({ type: 'resendSettled' })
    }
  }

  return {
    ...state,
    countdown,
    handleDigitsChange: (digits: string[]) => dispatch({ type: 'digitsChanged', digits }),
    handleSubmit,
    handleResend,
  }
}
