import { useState } from 'react'
import { BrowserRouter, Route, Routes, useInRouterContext, useNavigate } from 'react-router-dom'
import { logout } from './features/auth/utils/authSession'
import { useAuthSession } from './features/auth/hooks/useAuthSession'
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
// callers — re-verified 2026-07-17 against the running backend's OpenAPI document, which
// declares no security scheme for it at all. The client now sends `Authorization` on every
// generation call and refuses to send one without a session, so it no longer walks through the
// hole itself; the hole is still open to anyone who skips the client. This remains a product
// gate, not a security boundary — do not read it as one until the backend answers 401.
function DocumentGenerationFlow() {
  const navigate = useNavigate()
  // Subscribed, not sampled: a session that dies mid-flow (a refresh that failed while polling)
  // now re-renders this component by itself, instead of leaving a workspace on screen until the
  // user clicks something that no longer works.
  const isAuthenticated = useAuthSession()
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
  // session collapses to the landing rather than leaving a workspace on screen that every
  // request will refuse.
  if (step !== 'landing' && !isAuthenticated) {
    return <LandingPage onPrimaryCtaClick={startFlow} onLoginClick={goToLogin} />
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
        onLogoutClick={handleLogout}
      />
    )
  }

  return (
    <>
      <LandingPage
        onPrimaryCtaClick={startFlow}
        isAuthenticated={isAuthenticated}
        onLogoutClick={handleLogout}
        onLoginClick={goToLogin}
      />

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
