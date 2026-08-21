import { Header } from './Header'
import { LandingAdvantages } from './LandingAdvantages'
import { LandingComparison } from './LandingComparison'
import { LandingCta } from './LandingCta'
import { LandingExamples } from './LandingExamples'
import { LandingFaq } from './LandingFaq'
import { LandingHero } from './LandingHero'
import { LandingProcess } from './LandingProcess'
import { LandingShowcase } from './LandingShowcase'
import { LandingStats } from './LandingStats'
import { SiteFooter } from '../../../shared/components/SiteFooter'
import styles from './LandingPage.module.css'

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
    <div className={styles.landing}>
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
      {/* Immediately after «как это работает» and before the comparison: the visitor has just been
          told the three steps, and the natural next question is what comes out at the end of them.
          Placed before the comparison so the product's own output is judged on its merits before
          it is measured against anyone else's. */}
      <LandingExamples onPrimaryCtaClick={onPrimaryCtaClick} />
      <LandingComparison onPrimaryCtaClick={onPrimaryCtaClick} />
      <LandingFaq />
      <LandingCta onPrimaryCtaClick={onPrimaryCtaClick} />
      <SiteFooter />
    </div>
  )
}
