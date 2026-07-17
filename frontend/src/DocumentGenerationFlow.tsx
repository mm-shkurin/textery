import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { logout } from './features/auth/utils/authSession'
import { useAuthSession } from './features/auth/hooks/useAuthSession'
import {
  documentTypeFromWire,
  DOCUMENT_TYPE_LABELS,
  type DocumentType,
} from './features/generation/documentTypes'
import { HistoryPage } from './features/history/components/HistoryPage'
import type { GenerationMode } from './features/generation/components/ModeModal'
import { LandingPage } from './features/landing/components/LandingPage'
import { FlowLanding } from './FlowLanding'
import { ChatWorkspace } from './features/generation/components/ChatWorkspace'
import { ManualEditor } from './features/generation/components/ManualEditor'
import { useGeneration } from './features/generation/hooks/useGeneration'

type Step = 'landing' | 'type' | 'mode' | 'form' | 'history'

// The landing is the public shopfront and stays open to anonymous visitors — gating it would
// be gating marketing. Everything BEHIND it (type → mode → the workspace or the manual editor)
// needs an account.
//
// This gate is CLIENT-SIDE ONLY: it decides what UI to render, and it protects nothing on its
// own. Neither destination has a URL of its own — both are internal state — so the CTA is the
// only way in and gating the CTA closes the reachable path. A user who edits their own memory,
// or calls the API directly, walks straight past it.
//
// UPDATE 2026-07-17: the backend now enforces this for real, so the gate is no longer the only
// thing standing between an anonymous caller and a document. Re-measured by curl against the
// running stack — the earlier note here said the hole was open, and it is now closed:
//   POST /api/v1/generations, no header        -> 401 UNAUTHORIZED
//   POST /api/v1/generations, "Bearer garbage" -> 401 UNAUTHORIZED
//   POST /api/v1/documents,   no header        -> 401 UNAUTHORIZED
// This gate is still a product gate rather than the security boundary — the boundary is the
// 401 above. Keep them distinct: if the client's check is ever removed, the backend still
// refuses; if the backend's is ever removed, this one refuses nothing.
export function DocumentGenerationFlow() {
  const navigate = useNavigate()
  // Subscribed, not sampled: a session that dies mid-flow (a refresh that failed while polling)
  // now re-renders this component by itself, instead of leaving a workspace on screen until the
  // user clicks something that no longer works.
  const isAuthenticated = useAuthSession()
  const [step, setStep] = useState<Step>('landing')
  const [documentType, setDocumentType] = useState<DocumentType | null>(null)
  // `mode` picks the destination, and both are real now: 'auto' generates, 'manual' opens the
  // editor Story 5 built. It is still not sent to the backend — `POST /generations` has no mode
  // parameter — because the two modes are different screens, not one request with a flag.
  const [mode, setMode] = useState<GenerationMode | null>(null)
  // Set only when the editor is opened from history. Its presence is what tells ManualEditor to
  // GET an existing document instead of POSTing a new one — the `existingDocumentId` path
  // scenario 6.2 built and left unwired, because until history existed there was no entry point.
  const [openDocumentId, setOpenDocumentId] = useState<string | null>(null)
  const generation = useGeneration()

  const closeToLanding = () => {
    generation.reset()
    setStep('landing')
    setDocumentType(null)
    setMode(null)
    setOpenDocumentId(null)
  }

  const openHistory = () => {
    setStep('history')
  }

  // The row carries the wire's Cyrillic type; the app speaks its own. An unrecognised value
  // (the server added a type this build has never heard of) falls back to 'doklad' for the
  // breadcrumb label only — it is display text, and the document's real content comes from the
  // GET either way. Refusing to open the document over an unfamiliar label would be the worse
  // trade.
  const openDocumentFromHistory = (documentId: string, wireType: string) => {
    setDocumentType(documentTypeFromWire(wireType) ?? 'doklad')
    setMode('manual')
    setOpenDocumentId(documentId)
    setStep('form')
  }

  // Back from the editor goes to wherever the editor was opened FROM. Returning a
  // history-opened document to the mode modal would offer to pick a mode for a document that
  // already has one, and drop the visitor into a "create" flow they never started.
  const backFromEditor = () => {
    if (openDocumentId) {
      setOpenDocumentId(null)
      setMode(null)
      setStep('history')
      return
    }
    backToModeModal()
  }

  const backToModeModal = () => {
    setStep('mode')
    setMode(null)
  }

  // The CTA sends a signed-out visitor to REGISTER, not to sign in. Someone clicking "create a
  // generation" on a public landing is overwhelmingly a new visitor — the mockup calls this
  // button "Попробовать бесплатно" (01-landing.html:47), and answering "try it free" with a
  // password prompt asks for a password they do not have yet. Returning users have their own
  // door now: the "Войти" action in the header.
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

  // Signing out has to unwind the flow, not just the header: leaving `step` at 'form' would
  // keep an in-flight generation polling and drop the user back into the workspace the moment
  // anyone signs in again. `closeToLanding` already stops the poll and clears the selections.
  const handleLogout = () => {
    logout()
    closeToLanding()
  }

  // Belt and braces: the CTA is the only path that sets a non-landing step, but a session can
  // end mid-flow (storage cleared, a refresh that failed). Re-checking here means an expired
  // session collapses to the landing rather than leaving a workspace or an editor on screen
  // that every request will refuse.
  if (step !== 'landing' && !isAuthenticated) {
    return <LandingPage onPrimaryCtaClick={startFlow} onLoginClick={goToLogin} />
  }

  // Above the flow's own branches, and below the isAuthenticated gate: history is owner-scoped
  // by construction (both endpoints 401 without a token), so it never renders for a signed-out
  // visitor.
  if (step === 'history') {
    return (
      <HistoryPage onOpenDocument={openDocumentFromHistory} onBack={() => setStep('landing')} />
    )
  }

  if (step === 'form' && documentType && mode) {
    const documentTypeLabel = DOCUMENT_TYPE_LABELS[documentType]

    if (mode === 'manual') {
      // ManualEditor takes no sign-out action: it had none on Story 5's branch, and a merge is
      // not the place to invent one. That leaves the editor as the one signed-in screen with no
      // way out of the session — a real gap, but a NEW one, created by combining the branches
      // rather than present in either. It belongs to a follow-up, not to a conflict resolution.
      return (
        <ManualEditor
          documentType={documentType}
          documentTypeLabel={documentTypeLabel}
          onBack={backFromEditor}
          existingDocumentId={openDocumentId ?? undefined}
        />
      )
    }

    return (
      <ChatWorkspace
        documentTypeLabel={documentTypeLabel}
        state={generation.state}
        content={generation.content}
        volumePages={generation.volumePages}
        createdAt={generation.createdAt}
        error={generation.error}
        onSubmit={generation.submit}
        onReset={generation.reset}
        onLogoutClick={handleLogout}
      />
    )
  }

  return (
    <FlowLanding
      step={step as 'landing' | 'type' | 'mode'}
      documentType={documentType}
      isAuthenticated={isAuthenticated}
      onPrimaryCtaClick={startFlow}
      onLoginClick={goToLogin}
      onLogoutClick={handleLogout}
      onHistoryClick={openHistory}
      onSelectType={(type) => {
        setDocumentType(type)
        setStep('mode')
      }}
      onSelectMode={(selectedMode) => {
        setMode(selectedMode)
        setStep('form')
      }}
      onBackToType={() => setStep('type')}
      onClose={closeToLanding}
    />
  )
}
