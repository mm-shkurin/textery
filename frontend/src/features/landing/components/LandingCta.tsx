import './LandingSection.css'
import './LandingCta.css'

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
    <section className="landing-section landing-cta" data-testid="landing-cta">
      <div className="landing-section-head">
        <span className="landing-eyebrow">Передовой сервис</span>
        <h2 className="landing-cta-title">
          Создайте <span className="landing-cta-accent">первый текстовый документ</span> за 30
          секунд
        </h2>
        <p className="landing-section-lead">
          Без регистрации. Без кредитной карты. Просто попробуйте прямо сейчас.
        </p>
      </div>

      {onPrimaryCtaClick !== undefined && (
        <div className="landing-cta-action">
          <button
            type="button"
            className="btn-light"
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
