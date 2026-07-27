import { LandingPage } from '../features/landing/components/LandingPage'
import { TypeModal } from '../features/generation/components/TypeModal'
import { type DocumentType } from '../shared/documentTypes'

interface FlowLandingProps {
  step: 'landing' | 'type'
  isAuthenticated: boolean
  onPrimaryCtaClick: () => void
  onLoginClick: () => void
  onLogoutClick: () => void
  onHistoryClick: () => void
  onSelectType: (type: DocumentType) => void
  onClose: () => void
}

// The landing and the type modal that sits on top of it. Extracted from DocumentGenerationFlow
// on the 200-line limit, and it is a real seam rather than a slice taken to hit a number: this
// is the "choose what to make" surface, and everything it renders is presentational — no
// fetching, no session reading, no step transitions of its own. It is handed what to show and
// which callbacks to fire.
//
// Story 18 removed the mode-select modal: picking a type goes straight to generation, so this
// surface no longer renders a 'mode' step — the type modal is the only overlay left here.
export function FlowLanding({
  step,
  isAuthenticated,
  onPrimaryCtaClick,
  onLoginClick,
  onLogoutClick,
  onHistoryClick,
  onSelectType,
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
    </>
  )
}
