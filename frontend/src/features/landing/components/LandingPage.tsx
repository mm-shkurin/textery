import { Header } from './Header'
import { LandingFaq } from './LandingFaq'
import { LandingHero } from './LandingHero'
import { LandingShowcase } from './LandingShowcase'
import { LandingStats } from './LandingStats'
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
      <LandingFaq />

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <img className="footer-logo" src="/design/logo-textery.svg" alt="Textery" />
        </div>
      </footer>
    </div>
  )
}
