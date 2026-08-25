import landingSectionStyles from './LandingSection.module.css'
import { LandingSectionHead } from './LandingSectionHead'
import { LandingAdvantageArt } from './LandingAdvantageArt'
import styles from './LandingAdvantages.module.css'
import navbarButtonsStyles from '../../../shared/components/navbar/NavbarButtons.module.css'

interface LandingAdvantagesProps {
  onPrimaryCtaClick?: () => void
}

// Figma `Desktop` → `Advantages` (node 1337:6860): four white cards in a 2x2 grid under the
// section's own heading block, then the free-trial button.
//
// The copy is the frame's, verbatim, and so is the art: each card carries its own illustration,
// bleeding past the card's edge, with a 2x2 progress cluster in the top-left corner that fills up
// as the reader moves through the four. The cards used to hold an empty grey well in place of the
// art — a placeholder that read as four unfinished cards in the middle of the page.
//
// `kind` picks the illustration; the art itself lives in `LandingAdvantageArt` because each card's
// is a different composition of two or three overlapping renders, and inlining four of those here
// would bury the copy this file exists to hold.
const ADVANTAGES = [
  {
    kind: 'ai' as const,
    title: 'AI-генерация за 30 секунд',
    text: (
      <>
        <strong>Автоматическое создание</strong> структуры и содержания текста из вашего описания
      </>
    ),
  },
  {
    kind: 'editor' as const,
    title: 'Онлайн-редактор',
    text: (
      <>
        <strong>Полноценное редактирование</strong> текста <strong>прямо в браузере</strong> без
        установки Word
      </>
    ),
  },
  {
    kind: 'pdf' as const,
    title: 'PDF высокого качества',
    text: (
      <>
        Экспорт в PDF с <strong>сохранением всех элементов</strong> для печати и рассылки
      </>
    ),
  },
  {
    kind: 'backup' as const,
    title: 'Резервное копирование',
    text: (
      <>
        <strong>Автоматическое сохранение</strong> изменений, ничего не потеряется при сбое
      </>
    ),
  },
]

export function LandingAdvantages({ onPrimaryCtaClick }: LandingAdvantagesProps) {
  return (
    <section className={landingSectionStyles['landing-section']} data-testid="landing-advantages">
      <LandingSectionHead
        eyebrow="Возможности"
        title={
          <>
            <span className={landingSectionStyles['landing-section-title-accent']}>
              Учебные тексты под ключ
            </span>
            <br />
            на одной платформе
          </>
        }
        lead={
          <>
            Закрываем <strong>все этапы работы</strong> с текстом: от постановки задачи до готового
            файла
          </>
        }
      />

      <div
        className={`${landingSectionStyles['landing-section-body']} ${styles['advantages-grid']}`}
      >
        {ADVANTAGES.map((item, index) => (
          <article className={styles['advantage-card']} key={item.title}>
            {/* Four dots, the first `index + 1` of them filled: the frame's own way of saying
                how far down the list this card is. Decorative — the order is already carried by
                the DOM for anyone not looking at it. */}
            <div className={styles['advantage-dots']} aria-hidden="true">
              {[0, 1, 2, 3].map((dot) => (
                <i className={dot <= index ? styles['advantage-dot-on'] : undefined} key={dot} />
              ))}
            </div>

            <LandingAdvantageArt kind={item.kind} />

            <div className={styles['advantage-text-block']}>
              <h3 className={styles['advantage-title']}>{item.title}</h3>
              <p className={styles['advantage-text']}>{item.text}</p>
            </div>
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
