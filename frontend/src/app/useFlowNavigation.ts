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
  // server added a type this build has never heard of) falls back to 'doklad' rather than refusing
  // to open the document over an unfamiliar label — the real content comes from the GET either way.
  // NOTE: since scenario 1.1 threaded the type to the wire, `documentType` is no longer display-only
  // — `submitGeneration` puts it on a POST. The fabricated 'doklad' cannot reach the wire today,
  // because this path sets mode='manual' + openDocumentId and routes to ManualEditor, and every
  // route back to the create path passes through `selectType`. Any NEW path into step='form' that
  // skips `selectType` would inherit a silently fabricated wire value — thread a real type instead.
  const openDocumentFromHistory = (documentId: string, wireType: string) => {
    setDocumentType(documentTypeFromWire(wireType) ?? 'doklad')
    setMode('manual')
    setOpenDocumentId(documentId)
    setStep('form')
  }

  // Back from the editor goes to the list of the user's own works — from BOTH paths, and the
  // generated one is the change here. It used to land on the type step, which renders the
  // "Создание документа" modal over the landing: someone who had just finished a доклад was
  // answered with a prompt to start another one, and the only route to the document they had
  // just saved was to dismiss that modal and then find "Мои работы" in the header. Two
  // non-obvious clicks away from the one thing they were most likely to want next.
  //
  // History is where the work they just did now IS (a completed generation becomes a Document),
  // so it is both the honest destination and a forward-reachable one — the CTA in the landing
  // header is still one click from here for anyone who did want to start again.
  //
  // The generation is reset either way: leaving it set would keep a poll running, and — since
  // DocumentGenerationFlow suppresses `generationId` only when a history document is open — a
  // live generation sitting in flow state is a trap for the next thing that opens the editor.
  const backFromEditor = () => {
    generation.reset()
    setOpenDocumentId(null)
    setMode(null)
    setStep('history')
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
