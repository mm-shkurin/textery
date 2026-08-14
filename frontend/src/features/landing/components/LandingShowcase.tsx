import styles from './LandingShowcase.module.css'

interface LandingShowcaseProps {
  onPrimaryCtaClick?: () => void
}

// Figma `Desktop` (node 90:880), y=1028: a 40px heading over four 392x187 cards scattered
// around three overlapping 480px circles. Two cards are white, two are `#d2e2f2`.
const CARD_VARIANTS = ['muted', 'plain', 'plain', 'muted'] as const

export function LandingShowcase({ onPrimaryCtaClick }: LandingShowcaseProps) {
  return (
    <section className={styles.showcase} data-testid="landing-showcase">
      <h2 className={styles['showcase-title']}>
        Создайте свой первый <span className={styles['showcase-title-accent']}>доклад</span> за 30 сек
      </h2>

      <div className={styles['showcase-stage']} aria-hidden="true">
        <span className={styles['showcase-orb'] + ' ' + styles['showcase-orb-1']} />
        <span className={styles['showcase-orb'] + ' ' + styles['showcase-orb-2']} />
        <span className={styles['showcase-orb'] + ' ' + styles['showcase-orb-3']} />
        {CARD_VARIANTS.map((variant, index) => (
          <span
            className={`${styles['showcase-card']} showcase-card-${index + 1} showcase-card-${variant}`}
            key={index}
          />
        ))}
      </div>

      <button
        type="button"
        className={styles['showcase-cta']}
        data-testid="features-primary-cta-button"
        onClick={onPrimaryCtaClick}
      >
        Создать генерацию
      </button>
    </section>
  )
}
