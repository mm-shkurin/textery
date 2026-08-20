import landingSectionStyles from './LandingSection.module.css'
import styles from './LandingAdvantages.module.css'
import navbarButtonsStyles from '../../../shared/components/navbar/NavbarButtons.module.css'

interface LandingAdvantagesProps {
  onPrimaryCtaClick?: () => void
}

// Figma `Desktop` → `Advantages` (node 1337:6860): four white cards in a 2x2 grid under the
// section's own heading block, then the free-trial button.
//
// The copy is the frame's, verbatim. Each card in the design also carries an illustration; there
// is no exported art for those, so the card keeps the frame's recessed well in its place rather
// than shipping a stock image the design never chose — the well is what the art sits IN, so the
// layout is the design's either way.
const ADVANTAGES = [
  {
    title: 'AI-генерация за 30 секунд',
    text: 'Автоматическое создание структуры и содержания текста из вашего описания',
  },
  {
    title: 'Онлайн-редактор',
    text: 'Полноценное редактирование текста прямо в браузере без установки Word',
  },
  {
    title: 'PDF высокого качества',
    text: 'Экспорт в PDF с сохранением всех элементов для печати и рассылки',
  },
  {
    title: 'Резервное копирование',
    text: 'Автоматическое сохранение изменений, ничего не потеряется при сбое',
  },
]

export function LandingAdvantages({ onPrimaryCtaClick }: LandingAdvantagesProps) {
  return (
    <section className={landingSectionStyles['landing-section']} data-testid="landing-advantages">
      <div className={landingSectionStyles['landing-section-head']}>
        <span className={landingSectionStyles['landing-eyebrow']}>Возможности</span>
        <h2 className={landingSectionStyles['landing-section-title']}>
          Учебные тексты под ключ на одной платформе
        </h2>
        <p className={landingSectionStyles['landing-section-lead']}>
          Закрываем все этапы работы с текстом: от постановки задачи до готового файла
        </p>
      </div>

      <div
        className={`${landingSectionStyles['landing-section-body']} ${styles['advantages-grid']}`}
      >
        {ADVANTAGES.map((item) => (
          <article className={styles['advantage-card']} key={item.title}>
            <div className={styles['advantage-well']} aria-hidden="true" />
            <h3 className={styles['advantage-title']}>{item.title}</h3>
            <p className={styles['advantage-text']}>{item.text}</p>
          </article>
        ))}
      </div>

      {onPrimaryCtaClick !== undefined && (
        <div className={styles['advantages-action']}>
          <button
            type="button"
            className={navbarButtonsStyles['btn-light']}
            data-testid="advantages-primary-cta"
            onClick={onPrimaryCtaClick}
          >
            Попробовать бесплатно
          </button>
        </div>
      )}
    </section>
  )
}
