import { useState } from 'react'
import { BrowserRouter, Route, Routes, useInRouterContext } from 'react-router-dom'
import { LandingPage } from './features/landing/components/LandingPage'
import { TypeModal } from './features/generation/components/TypeModal'
import type { DocumentType } from './features/generation/documentTypes'
import { ModeModal, type GenerationMode } from './features/generation/components/ModeModal'
import { ChatWorkspace } from './features/generation/components/ChatWorkspace'
import { useGeneration } from './features/generation/hooks/useGeneration'
import { RegisterForm } from './features/auth/components/RegisterForm'

type Step = 'landing' | 'type' | 'mode' | 'form'

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  doklad: 'Доклад',
  essay: 'Эссе',
  sochinenie: 'Сочинение',
  referat: 'Реферат',
}

function DocumentGenerationFlow() {
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
      <LandingPage onPrimaryCtaClick={() => setStep('type')} />

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
