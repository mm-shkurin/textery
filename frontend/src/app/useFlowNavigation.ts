import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { logout } from '../features/auth/utils/authSession'
import { useAuthSession } from '../features/auth/hooks/useAuthSession'
import { documentTypeFromWire, type DocumentType } from '../features/generation/documentTypes'
import type { GenerationMode } from '../features/generation/components/ModeModal'
import { useGeneration } from '../features/generation/hooks/useGeneration'

export type Step = 'landing' | 'type' | 'mode' | 'form' | 'history'

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

  const backToModeModal = () => {
    setStep('mode')
    setMode(null)
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

  // Back from the editor goes to wherever the editor was opened FROM. Returning a history-opened
  // document to the mode modal would offer to pick a mode for a document that already has one,
  // and drop the visitor into a "create" flow they never started.
  const backFromEditor = () => {
    if (openDocumentId) {
      setOpenDocumentId(null)
      setMode(null)
      setStep('history')
      return
    }
    backToModeModal()
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

  const selectType = (type: DocumentType) => {
    setDocumentType(type)
    setStep('mode')
  }

  const selectMode = (selected: GenerationMode) => {
    setMode(selected)
    setStep('form')
  }

  return {
    step,
    documentType,
    mode,
    openDocumentId,
    isAuthenticated,
    generation,
    openHistory: () => setStep('history'),
    backToTypeModal: () => setStep('type'),
    backToLanding: () => setStep('landing'),
    closeToLanding,
    openDocumentFromHistory,
    backFromEditor,
    startFlow,
    goToLogin,
    handleLogout,
    selectType,
    selectMode,
  }
}
