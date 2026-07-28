import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { logout } from '../features/auth/utils/authSession'
import { useAuthSession } from '../features/auth/hooks/useAuthSession'
import {
  DEFAULT_DOCUMENT_TYPE,
  documentTypeFromWire,
  type DocumentType,
} from '../shared/documentTypes'
import { useGeneration } from '../features/generation/hooks/useGeneration'

// 'auto' generates from a topic, 'manual' opens the editor. Both are real destinations, not a
// request flag — they are different screens. Story 18 dropped the mode-select modal, so on the
// create path `mode` is always 'auto'; 'manual' now survives only on the history-open path.
export type GenerationMode = 'auto' | 'manual'

export type Step = 'landing' | 'type' | 'form' | 'history'

// Every transition the flow can make, and the state they move between. Split from
// DocumentGenerationFlow because the two were a state machine and its renderer sharing a file:
// the component's job is "given this state, which screen", and each transition's *reason* is a
// paragraph that has nothing to do with rendering.
export function useFlowNavigation() {
  const navigate = useNavigate()
  // Subscribed, not sampled: a session that dies mid-flow (a refresh that failed while polling)
  // re-renders the flow by itself, instead of leaving a workspace on screen until the user
  // clicks something that no longer works.
  const isAuthenticated = useAuthSession()
  const generation = useGeneration()
  const [step, setStep] = useState<Step>('landing')
  const [documentType, setDocumentType] = useState<DocumentType | null>(null)
  // `mode` picks the destination, and both are real: 'auto' generates, 'manual' opens the
  // editor. It is not sent to the backend — `POST /generations` has no mode parameter — because
  // the two modes are different screens, not one request with a flag.
  const [mode, setMode] = useState<GenerationMode | null>(null)
  // Set only when the editor is opened from history. Its presence is what tells ManualEditor to
  // GET an existing document instead of POSTing a new one.
  const [openDocumentId, setOpenDocumentId] = useState<string | null>(null)

  const closeToLanding = () => {
    generation.reset()
    setStep('landing')
    setDocumentType(null)
    setMode(null)
    setOpenDocumentId(null)
  }

  // The row carries the wire's Cyrillic type; the app speaks its own. An unrecognised value (the
  // server added a type this build has never heard of) falls back to 'doklad' for the breadcrumb
  // LABEL only — it is display text, and the document's real content comes from the GET either
  // way. Refusing to open the document over an unfamiliar label would be the worse trade.
  const openDocumentFromHistory = (documentId: string, wireType: string) => {
    setDocumentType(documentTypeFromWire(wireType) ?? 'doklad')
    setMode('manual')
    setOpenDocumentId(documentId)
    setStep('form')
  }

  // Back from the editor goes to wherever the editor was opened FROM. A history-opened document
  // returns to history — offering to pick a mode for a document that already has one, and dropping
  // the visitor into a "create" flow they never started, would be wrong.
  //
  // A NEW (non-history) document returns to the type step: story 18 removed the mode-select modal,
  // so 'mode' is no longer a destination. Going back to 'type' lets the user pick a different
  // document type, and resets any in-flight generation so the poll is not left running.
  const backFromEditor = () => {
    if (openDocumentId) {
      setOpenDocumentId(null)
      setMode(null)
      setStep('history')
      return
    }
    generation.reset()
    setMode(null)
    setStep('type')
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
    setStep('type')
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

  // Story 18 1.1: picking a type goes STRAIGHT to generation. The mode-select modal is gone, so
  // there is no intermediate 'mode' step and no mode to choose — the create path is always 'auto'.
  // `openDocumentId` stays null, which is what tells the workspace to POST a new generation rather
  // than GET an existing document.
  const selectType = (type: DocumentType) => {
    setDocumentType(type)
    setMode('auto')
    setStep('form')
  }

  // The composer only knows the topic; the type the user picked lives here, in flow state. This
  // is the join, and it is the whole point of scenario 1.1 — with the mode modal gone the type
  // card is the LAST choice before the POST, so if it is not carried across this seam the wire
  // says 'доклад' no matter which card was pressed. The fallback is unreachable in practice
  // (the workspace only renders at `step === 'form' && documentType`) and exists so the composer
  // cannot post a typeless request.
  const submitGeneration = (topic: string) => {
    generation.submit(topic, documentType ?? DEFAULT_DOCUMENT_TYPE)
  }

  return {
    step,
    documentType,
    mode,
    openDocumentId,
    isAuthenticated,
    generation,
    submitGeneration,
    openHistory: () => setStep('history'),
    backToLanding: () => setStep('landing'),
    closeToLanding,
    openDocumentFromHistory,
    backFromEditor,
    startFlow,
    goToLogin,
    handleLogout,
    selectType,
  }
}
