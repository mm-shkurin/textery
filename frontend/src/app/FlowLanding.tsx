import { LandingPage } from '../features/landing/components/LandingPage'
import { TypeModal } from '../features/generation/components/TypeModal'
import { ModeModal, type GenerationMode } from '../features/generation/components/ModeModal'
import { DOCUMENT_TYPE_LABELS, type DocumentType } from '../features/generation/documentTypes'

interface FlowLandingProps {
  step: 'landing' | 'type' | 'mode'
  documentType: DocumentType | null
  isAuthenticated: boolean
  onPrimaryCtaClick: () => void
  onLoginClick: () => void
  onLogoutClick: () => void
  onHistoryClick: () => void
  onSelectType: (type: DocumentType) => void
  onSelectMode: (mode: GenerationMode) => void
  onBackToType: () => void
  onClose: () => void
}

// The landing and the two modals that sit on top of it. Extracted from DocumentGenerationFlow
// on the 200-line limit, and it is a real seam rather than a slice taken to hit a number: this
// is the "choose what to make" surface, and everything it renders is presentational — no
// fetching, no session reading, no step transitions of its own. It is handed what to show and
// which callbacks to fire.
export function FlowLanding({
  step,
  documentType,
  isAuthenticated,
  onPrimaryCtaClick,
  onLoginClick,
  onLogoutClick,
  onHistoryClick,
  onSelectType,
  onSelectMode,
  onBackToType,
  onClose,
}: FlowLandingProps) {
  return (
    <>
      <LandingPage
        onPrimaryCtaClick={onPrimaryCtaClick}
        isAuthenticated={isAuthenticated}
        onLogoutClick={onLogoutClick}
        onLoginClick={onLoginClick}
        onHistoryClick={onHistoryClick}
      />

      {step === 'type' && <TypeModal onSelect={onSelectType} onClose={onClose} />}

      {step === 'mode' && documentType && (
        <ModeModal
          documentTypeLabel={DOCUMENT_TYPE_LABELS[documentType]}
          onSelect={onSelectMode}
          onBack={onBackToType}
          onClose={onClose}
        />
      )}
    </>
  )
}
