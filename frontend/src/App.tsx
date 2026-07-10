import { useState } from 'react'
import { LandingPage } from './features/landing/components/LandingPage'
import { TypeModal, type DocumentType } from './features/generation/components/TypeModal'
import { ModeModal, type GenerationMode } from './features/generation/components/ModeModal'
import { ChatWorkspace } from './features/generation/components/ChatWorkspace'
import { useGeneration } from './features/generation/hooks/useGeneration'

type Step = 'landing' | 'type' | 'mode' | 'form'

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  doklad: 'Доклад',
  essay: 'Эссе',
  sochinenie: 'Сочинение',
  referat: 'Реферат',
}

function App() {
  const [step, setStep] = useState<Step>('landing')
  const [documentType, setDocumentType] = useState<DocumentType | null>(null)
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

export default App
