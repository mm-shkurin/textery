import { LandingPage } from '../features/landing/components/LandingPage'
import type { LandingChromeProps } from '../features/landing/utils/landingChrome'
import { TypeModal } from '../features/generation/components/TypeModal'
import { type DocumentType } from '../shared/domain/documentTypes'

// The chrome props come from `LandingChromeProps` rather than being respelled here, which is the
// whole point of that type: a sixth landing action has to break every forwarder that has not been
// updated, and a hand-written copy in this file would compile while silently dropping it.
// Required here, optional there — this component always has all four to give.
interface FlowLandingProps extends Required<LandingChromeProps> {
  step: 'landing' | 'type'
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
