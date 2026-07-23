import './LandingShowcase.css'

interface LandingShowcaseProps {
  onPrimaryCtaClick?: () => void
}

// Figma `Desktop` (node 90:880), y=1028: a 40px heading over four 392x187 cards scattered
// around three overlapping 480px circles. Two cards are white, two are `#d2e2f2`.
const CARD_VARIANTS = ['muted', 'plain', 'plain', 'muted'] as const

export function LandingShowcase({ onPrimaryCtaClick }: LandingShowcaseProps) {
  return (
    <section className="showcase" data-testid="landing-showcase">
      <h2 className="showcase-title">
        Создайте свой первый <span className="showcase-title-accent">доклад</span> за 30 сек
      </h2>

      <div className="showcase-stage" aria-hidden="true">
        <span className="showcase-orb showcase-orb-1" />
        <span className="showcase-orb showcase-orb-2" />
        <span className="showcase-orb showcase-orb-3" />
        {CARD_VARIANTS.map((variant, index) => (
          <span
            className={`showcase-card showcase-card-${index + 1} showcase-card-${variant}`}
            key={index}
          />
        ))}
      </div>

      <button
        type="button"
        className="showcase-cta"
        data-testid="features-primary-cta-button"
        onClick={onPrimaryCtaClick}
      >
        Создать генерацию
      </button>
    </section>
  )
}
