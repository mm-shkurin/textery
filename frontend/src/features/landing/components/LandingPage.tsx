import './LandingPage.css'

interface LandingPageProps {
  onPrimaryCtaClick?: () => void
}

export function LandingPage({ onPrimaryCtaClick }: LandingPageProps) {
  return (
    <div className="hero">
      <h1 data-testid="hero-heading">Word онлайн</h1>
      <p className="subtitle" data-testid="hero-subheading">
        С возможностью генерации через нейросеть Textery AI
      </p>
      <button
        type="button"
        className="btn-primary large"
        data-testid="hero-primary-cta-button"
        onClick={onPrimaryCtaClick}
      >
        Создать генерацию
      </button>
    </div>
  )
}
