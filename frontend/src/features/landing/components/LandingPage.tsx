import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import { Header } from './Header'
import './LandingPage.css'

interface LandingPageProps {
  onPrimaryCtaClick?: () => void
}

const FEATURES = [
  {
    title: 'Множество шаблонов',
    text: 'Используйте готовые решения, чтобы значительно ускорить свою работу',
  },
  {
    title: 'Стили для текста',
    text: 'Строгие, курсивные, жирные, тонкие — выбирайте подходящие шрифты для работы',
  },
  {
    title: 'Загрузка элементов',
    text: 'Всё, что может понадобиться для доклада, уже есть в библиотеке',
  },
  {
    title: 'Ручной режим',
    text: 'В редакторе есть возможность создавать доклад вручную',
  },
]

export function LandingPage({ onPrimaryCtaClick }: LandingPageProps) {
  return (
    <div className="landing">
      <Header onPrimaryCtaClick={onPrimaryCtaClick} />

      <div className="hero">
        <h1 data-testid="hero-heading">Word онлайн</h1>
      </div>

      <div className="hero-collage-wrap">
        <img className="hero-collage" src="/hero-collage.svg" alt="" aria-hidden="true" />
      </div>

      <div className="trust-row">
        <div className="trust-avatars">
          {Array.from({ length: 4 }).map((_, i) => (
            <span className="trust-avatar" key={i} />
          ))}
        </div>
        <span className="trust-text">Нам доверяют тысячи пользователей - присоединяйтесь!</span>
      </div>

      <section className="features">
        <h2>Редактор нового поколения</h2>
        <p className="features-subtitle">Доклады только по вашим правилам: они будут выглядеть, как нужно</p>

        <div className="features-panel">
          <div className="feature-cards">
            {FEATURES.map((feature) => (
              <div className="feature-card" key={feature.title}>
                <div className="feature-card-text">
                  <h3>{feature.title}</h3>
                  <p>{feature.text}</p>
                </div>
                <PlaceholderImage className="feature-icon" />
              </div>
            ))}
          </div>
          <PlaceholderImage className="feature-hero-image" />
        </div>

        <button type="button" className="btn-light centered" onClick={onPrimaryCtaClick}>
          Создать генерацию
        </button>
      </section>

      <footer className="landing-footer">
        <span className="footer-wordmark-muted">Textery</span>{' '}
        <span className="footer-wordmark">AI</span>
      </footer>
    </div>
  )
}
