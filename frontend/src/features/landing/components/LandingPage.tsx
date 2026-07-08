import './LandingPage.css'

export function LandingPage() {
  return (
    <div className="hero">
      <h1 data-testid="hero-heading">Word онлайн</h1>
      <p className="subtitle" data-testid="hero-subheading">
        С возможностью генерации через нейросеть Textery AI
      </p>
      <button type="button" className="btn-primary large" data-testid="hero-primary-cta-button">
        Создать генерацию
      </button>
    </div>
  )
}
