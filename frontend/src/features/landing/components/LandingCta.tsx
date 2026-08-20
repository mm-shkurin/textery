import landingSectionStyles from './LandingSection.module.css'
import styles from './LandingCta.module.css'
import navbarButtonsStyles from '../../../shared/components/navbar/NavbarButtons.module.css'

interface LandingCtaProps {
  onPrimaryCtaClick?: () => void
}

// Figma `Desktop` → `CTA` (node 1290:11260): the page's closing block — an eyebrow, a two-line
// 44/53 heading whose second half is brand blue, one line of reassurance, and the free-trial
// button, centred inside a ring of rounded document thumbnails.
//
// The ring is left out: it is 17 pieces of art with no export, and faking it with placeholder
// rectangles would put a wall of empty grey boxes around the last thing the page says. The block
// keeps the frame's own composition without it.
export function LandingCta({ onPrimaryCtaClick }: LandingCtaProps) {
  return (
    <section
      className={`${landingSectionStyles['landing-section']} ${styles['landing-cta']}`}
      data-testid="landing-cta"
    >
      <div className={landingSectionStyles['landing-section-head']}>
        <span className={landingSectionStyles['landing-eyebrow']}>Передовой сервис</span>
        <h2 className={styles['landing-cta-title']}>
          Создайте <span className={styles['landing-cta-accent']}>первый текстовый документ</span>{' '}
          за 30 секунд
        </h2>
        <p className={landingSectionStyles['landing-section-lead']}>
          Без регистрации. Без кредитной карты. Просто попробуйте прямо сейчас.
        </p>
      </div>

      {onPrimaryCtaClick !== undefined && (
        <div className={styles['landing-cta-action']}>
          <button
            type="button"
            className={navbarButtonsStyles['btn-light']}
            data-testid="cta-primary-cta"
            onClick={onPrimaryCtaClick}
          >
            Попробовать бесплатно
          </button>
        </div>
      )}
    </section>
  )
}
