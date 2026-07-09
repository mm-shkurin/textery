import { useState } from 'react'
import { LandingPage } from './features/landing/components/LandingPage'
import { TypeModal, type DocumentType } from './features/generation/components/TypeModal'
import { ModeModal, type GenerationMode } from './features/generation/components/ModeModal'

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

  const closeToLanding = () => {
    setStep('landing')
    setDocumentType(null)
    setMode(null)
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

      {step === 'form' && (
        <div data-testid="generation-form-placeholder">
          Форма генерации ({documentType}, {mode}) — следующий work unit (Scenario 4.1).
        </div>
      )}
    </>
  )
}

export default App
