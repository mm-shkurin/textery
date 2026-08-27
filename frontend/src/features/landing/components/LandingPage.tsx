import { Header } from './Header'
import type { LandingChromeProps } from '../utils/landingChrome'
import { LandingAdvantages } from './LandingAdvantages'
import { LandingComparison } from './LandingComparison'
import { LandingExport } from './LandingExport'
import { LandingCta } from './LandingCta'
import { LandingFaq } from './LandingFaq'
import { LandingHero } from './LandingHero'
import { LandingProcess } from './LandingProcess'
import { LandingShowcase } from './LandingShowcase'
import { LandingStats } from './LandingStats'
import { LandingTrustedBy } from './LandingTrustedBy'
import { SiteFooter } from '../../../shared/components/SiteFooter'
import styles from './LandingPage.module.css'

export function LandingPage({ onPrimaryCtaClick, ...chrome }: LandingChromeProps) {
  return (
    <div className={styles.landing}>
      <Header onPrimaryCtaClick={onPrimaryCtaClick} {...chrome} />

      {/* The frame's order, top to bottom (Figma `Desktop`, node 90:880): the hero with its
          prompt bar and the three stat cards, the logos of who trusts the product, the three
          steps, what the platform does, how its Russian compares, the lossless export, the dark
          table against competitors, the questions, then the closing ask.

          «Примеры готовых работ» is gone with this pass: the redrawn frame replaces it with the
          export section, and keeping a section the design no longer has would leave the page
          claiming something nobody drew. */}
      <LandingHero onPromptSubmit={onPrimaryCtaClick} />
      <LandingStats />
      <LandingTrustedBy />
      <LandingProcess />
      <LandingAdvantages onPrimaryCtaClick={onPrimaryCtaClick} />
      <LandingShowcase onPrimaryCtaClick={onPrimaryCtaClick} />
      <LandingExport />
      <LandingComparison onPrimaryCtaClick={onPrimaryCtaClick} />
      <LandingFaq />
      <LandingCta onPrimaryCtaClick={onPrimaryCtaClick} />
      <SiteFooter />
    </div>
  )
}
