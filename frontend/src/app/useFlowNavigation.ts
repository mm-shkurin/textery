import { useReducer } from 'react'
import { useNavigate } from 'react-router-dom'
import { logout } from '../shared/session/authSession'
import { useAuthSession } from '../features/auth/hooks/useAuthSession'
import { DEFAULT_DOCUMENT_TYPE, type DocumentType } from '../shared/documentTypes'
import type { GenerationParameters } from '../features/generation/utils/generationParameters'
import { useGeneration } from '../features/generation/hooks/useGeneration'
import { flowReducer, INITIAL_FLOW_STATE } from './flowNavigationState'

export type { GenerationMode, Step } from './flowNavigationState'

// Every transition the flow can make, and the state they move between. Split from
// DocumentGenerationFlow because the two were a state machine and its renderer sharing a file:
// the component's job is "given this state, which screen", and each transition's *reason* is a
// paragraph that has nothing to do with rendering.
//
// The position itself — step, type, mode, open document — is one value moved by named actions in
// flowNavigationState; what stays here is the part that is NOT a state transition: navigation,
// the session, and stopping the poll.
export function useFlowNavigation() {
  const navigate = useNavigate()
  // Subscribed, not sampled: a session that dies mid-flow (a refresh that failed while polling)
  // re-renders the flow by itself, instead of leaving a workspace on screen until the user
  // clicks something that no longer works.
  const isAuthenticated = useAuthSession()
  const generation = useGeneration()
  const [flow, dispatch] = useReducer(flowReducer, INITIAL_FLOW_STATE)

  const closeToLanding = () => {
    generation.reset()
    dispatch({ type: 'closeToLanding' })
  }

  // The generation is reset on the way out of the editor: leaving it set would keep a poll
  // running, and — since DocumentGenerationFlow suppresses `generationId` only when a history
  // document is open — a live generation sitting in flow state is a trap for the next thing that
  // opens the editor.
  const backFromEditor = () => {
    generation.reset()
    dispatch({ type: 'backFromEditor' })
  }

  // The CTA sends a signed-out visitor to REGISTER, not to sign in. Someone clicking "create a
  // generation" on a public landing is overwhelmingly a new visitor — the mockup calls this
  // button "Попробовать бесплатно" (01-landing.html:47), and answering "try it free" with a
  // password prompt asks for a password they do not have yet. Returning users have their own
  // door: the "Войти" action in the header.
  //
  // Registration lands them back here signed in (see postVerifySignIn), so the CTA still leads
  // where it says it does — just via the one screen a new user can actually complete.
  const startFlow = () => {
    if (!isAuthenticated) {
      navigate('/register')
      return
    }
    dispatch({ type: 'startCreation' })
  }

  // `from` so signing in returns them to what they were doing, instead of dropping them on the
  // landing to hunt for the button again.
  const goToLogin = () => {
    navigate('/login', { state: { from: '/' } })
  }

  // Signing out has to unwind the flow, not just the header: leaving `step` at 'form' would keep
  // an in-flight generation polling and drop the user back into the workspace the moment anyone
  // signs in again. `closeToLanding` already stops the poll and clears the selections.
  const handleLogout = () => {
    logout()
    closeToLanding()
  }

  // The composer only knows the topic; the type the user picked lives here, in flow state. This
  // is the join, and it is the whole point of scenario 1.1 — with the mode modal gone the type
  // card is the LAST choice before the POST, so if it is not carried across this seam the wire
  // says 'доклад' no matter which card was pressed. The fallback is unreachable in practice
  // (the workspace only renders at `step === 'form' && documentType`) and exists so the composer
  // cannot post a typeless request.
  const submitGeneration = (topic: string, parameters?: GenerationParameters) => {
    generation.submit(topic, flow.documentType ?? DEFAULT_DOCUMENT_TYPE, parameters)
  }

  return {
    step: flow.step,
    documentType: flow.documentType,
    mode: flow.mode,
    openDocumentId: flow.openDocumentId,
    isAuthenticated,
    generation,
    submitGeneration,
    openHistory: () => dispatch({ type: 'openHistory' }),
    backToLanding: () => dispatch({ type: 'backToLanding' }),
    closeToLanding,
    openDocumentFromHistory: (documentId: string, wireType: string) =>
      dispatch({ type: 'openDocumentFromHistory', documentId, wireType }),
    backFromEditor,
    startFlow,
    goToLogin,
    handleLogout,
    selectType: (documentType: DocumentType) =>
      dispatch({ type: 'selectDocumentType', documentType }),
  }
}
