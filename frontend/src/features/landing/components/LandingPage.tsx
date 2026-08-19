import { Header } from './Header'
import { LandingAdvantages } from './LandingAdvantages'
import { LandingComparison } from './LandingComparison'
import { LandingCta } from './LandingCta'
import { LandingFaq } from './LandingFaq'
import { LandingHero } from './LandingHero'
import { LandingProcess } from './LandingProcess'
import { LandingShowcase } from './LandingShowcase'
import { LandingStats } from './LandingStats'
import { SiteFooter } from '../../../shared/components/SiteFooter'
import './LandingPage.css'

interface LandingPageProps {
  onPrimaryCtaClick?: () => void
  isAuthenticated?: boolean
  onLogoutClick?: () => void
  onLoginClick?: () => void
  onHistoryClick?: () => void
}

export function LandingPage({
  onPrimaryCtaClick,
  isAuthenticated,
  onLogoutClick,
  onLoginClick,
  onHistoryClick,
}: LandingPageProps) {
  return (
    <div className="landing">
      <Header
        onPrimaryCtaClick={onPrimaryCtaClick}
        isAuthenticated={isAuthenticated}
        onLogoutClick={onLogoutClick}
        onLoginClick={onLoginClick}
        onHistoryClick={onHistoryClick}
      />

      <LandingHero onPromptSubmit={onPrimaryCtaClick} />
      <LandingStats />
      <LandingShowcase onPrimaryCtaClick={onPrimaryCtaClick} />
      {/* The order is the frame's, top to bottom: what the product does, how it is used, how it
          compares, the questions, then the closing ask. */}
      <LandingAdvantages onPrimaryCtaClick={onPrimaryCtaClick} />
      <LandingProcess />
      <LandingComparison onPrimaryCtaClick={onPrimaryCtaClick} />
      <LandingFaq />
      <LandingCta onPrimaryCtaClick={onPrimaryCtaClick} />
      <SiteFooter />
    </div>
  )
}
