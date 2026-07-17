import { useState } from 'react'
import { BrowserRouter, Route, Routes, useInRouterContext, useNavigate } from 'react-router-dom'
import { isAuthenticated } from './features/auth/utils/authSession'
import { LandingPage } from './features/landing/components/LandingPage'
import { TypeModal } from './features/generation/components/TypeModal'
import type { DocumentType } from './features/generation/documentTypes'
import { ModeModal, type GenerationMode } from './features/generation/components/ModeModal'
import { ChatWorkspace } from './features/generation/components/ChatWorkspace'
import { useGeneration } from './features/generation/hooks/useGeneration'
import { RegisterForm } from './features/auth/components/RegisterForm'
import { LoginForm } from './features/auth/components/LoginForm'
import { VerifyCodeForm } from './features/auth/components/VerifyCodeForm'

type Step = 'landing' | 'type' | 'mode' | 'form'

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  doklad: 'Доклад',
  essay: 'Эссе',
  sochinenie: 'Сочинение',
  referat: 'Реферат',
}

// The landing is the public shopfront and stays open to anonymous visitors — gating it would
// be gating marketing. Everything BEHIND it (type → mode → the workspace) needs an account.
//
// This gate is CLIENT-SIDE ONLY: it decides what UI to render, and it protects nothing on its
// own. The workspace has no URL of its own — it is internal state — so the CTA is the only way
// in and gating the CTA closes the reachable path. But a user who edits their own memory, or
// simply calls the API directly, walks straight past it. Real protection is the backend
// refusing requests without a token; today `POST /api/v1/generations` still serves anonymous
// callers (verified 2026-07-16: 400 for a malformed body, not 401). Until that changes and the
// client sends `Authorization`, this is a product gate, not a security boundary — do not read
// it as one.
function DocumentGenerationFlow() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('landing')
  const [documentType, setDocumentType] = useState<DocumentType | null>(null)
  // `mode` is UI-only: backend has no mode parameter yet, only 'auto' is selectable today.
  const [mode, setMode] = useState<GenerationMode | null>(null)
  const generation = useGeneration()

  const closeToLanding = () => {
    generation.reset()
    setStep('landing')
    setDocumentType(null)
    setMode(null)
  }

  const startFlow = () => {
    if (!isAuthenticated()) {
      // `from` so login returns them to what they were trying to do, instead of dropping them
      // on the landing to hunt for the button again.
      navigate('/login', { state: { from: '/' } })
      return
    }
    setStep('type')
  }

  // Belt and braces: the CTA is the only path that sets a non-landing step, but a session can
  // end mid-flow (tab storage cleared, another tab logging out). Re-checking at render means an
  // expired session collapses to the landing rather than leaving a workspace on screen that
  // every request will refuse.
  if (step !== 'landing' && !isAuthenticated()) {
    return <LandingPage onPrimaryCtaClick={startFlow} />
  }

  if (step === 'form' && documentType && mode) {
    return (
      <ChatWorkspace
        documentTypeLabel={DOCUMENT_TYPE_LABELS[documentType]}
        state={generation.state}
        content={generation.content}
        volumePages={generation.volumePages}
        createdAt={generation.createdAt}
        error={generation.error}
        onSubmit={generation.submit}
        onReset={generation.reset}
      />
    )
  }

  return (
    <>
      <LandingPage onPrimaryCtaClick={startFlow} />

      {step === 'type' && (
        <TypeModal
          onSelect={(type) => {
            setDocumentType(type)
            setStep('mode')
          }}
          onClose={closeToLanding}
        />
      )}

      {step === 'mode' && documentType && (
        <ModeModal
          documentTypeLabel={DOCUMENT_TYPE_LABELS[documentType]}
          onSelect={(selectedMode) => {
            setMode(selectedMode)
            setStep('form')
          }}
          onBack={() => setStep('type')}
          onClose={closeToLanding}
        />
      )}
    </>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/login" element={<LoginForm />} />
      <Route path="/verify" element={<VerifyCodeForm />} />
      <Route path="/*" element={<DocumentGenerationFlow />} />
    </Routes>
  )
}

// Renders its own BrowserRouter when not already inside one (production entry
// via main.tsx omits an outer Router), but defers to an existing Router
// context when a test wraps App in MemoryRouter directly.
function App() {
  const isInsideRouter = useInRouterContext()

  if (isInsideRouter) {
    return <AppRoutes />
  }

  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App
