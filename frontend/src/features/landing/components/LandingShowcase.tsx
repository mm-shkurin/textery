import styles from './LandingShowcase.module.css'
import landingSectionStyles from './LandingSection.module.css'
import { LandingSectionHead } from './LandingSectionHead'
import navbarButtonsStyles from '../../../shared/components/navbar/NavbarButtons.module.css'

interface LandingShowcaseProps {
  onPrimaryCtaClick?: () => void
}

// Figma `Desktop` → `Landuage` (node 1346:7441): two white cards on a pale panel, one per engine,
// each scoring three qualities of Russian-language output on a 0–100 bar.
//
// It replaces the orbs-and-empty-cards stage this component used to draw. That stage rendered four
// blank rectangles behind three blurred circles — art that was never exported — so on the real
// page it was 900px of empty blue between a heading and a button. The section the frame actually
// puts there says something, and it is the product's own argument for itself.
const SCORES = [
  {
    engine: 'Textery',
    ours: true,
    metrics: [
      {
        score: 97,
        title: 'Точность терминов',
        text: 'Использует корректную деловую лексику без англицизмов и дословных переводов',
      },
      {
        score: 92,
        title: 'Естественный стиль речи',
        text: 'Textery AI изначально обучена понимать и генерировать на русском языке',
      },
      {
        score: 94,
        title: 'Сохранение контекста',
        text: 'Понимает сложные запросы и сохраняет логику и нюансы даже в многосоставных задачах',
      },
    ],
  },
  {
    engine: 'Другие ИИ',
    ours: false,
    metrics: [
      {
        score: 61,
        title: 'Точность терминов',
        text: 'Не адаптируют лексику под русскоязычную аудиторию, подставляя английские термины',
      },
      {
        score: 56,
        title: 'Естественный стиль речи',
        text: 'Обучены на английском языке и переводят русский текст, теряя смысл и контекст',
      },
      {
        score: 47,
        title: 'Сохранение контекста',
        text: 'Упрощают или искажают исходную задачу, теряя второстепенные и ключевые смыслы',
      },
    ],
  },
]

export function LandingShowcase({ onPrimaryCtaClick }: LandingShowcaseProps) {
  return (
    <section className={landingSectionStyles['landing-section']} data-testid="landing-showcase">
      <LandingSectionHead
        eyebrow="Преимущества"
        title="Лучшее качество на русском языке"
        lead="Нативная поддержка русского против автоперевода конкурентов. Сравнение генерации одного промпта"
      />

      <div
        className={`${landingSectionStyles['landing-section-body']} ${styles['showcase-panel']}`}
      >
        {SCORES.map((column) => (
          <article className={styles['showcase-card']} key={column.engine}>
            <p
              className={`${styles['showcase-chip']}${column.ours ? ' ' + styles['showcase-chip-ours'] : ''}`}
            >
              {column.engine}
            </p>
            {column.metrics.map((metric) => (
              <div className={styles['showcase-metric']} key={metric.title}>
                <div className={styles['showcase-scale']} aria-hidden="true">
                  <span>0%</span>
                  <span>100%</span>
                </div>
                {/* A real <progress>: the number beside it is the same value, and a bar drawn
                    with two <div>s tells an assistive technology nothing about what it fills. */}
                <progress className={styles['showcase-bar']} value={metric.score} max={100}>
                  {metric.score}%
                </progress>
                <p className={styles['showcase-score']}>{metric.score}%</p>
                <h3 className={styles['showcase-metric-title']}>{metric.title}</h3>
                <p className={styles['showcase-metric-text']}>{metric.text}</p>
              </div>
            ))}
          </article>
        ))}
      </div>

      <div className={styles['showcase-action']}>
        <button
          type="button"
          className={navbarButtonsStyles['btn-light']}
          data-testid="features-primary-cta-button"
          onClick={onPrimaryCtaClick}
        >
          Создать генерацию
        </button>
      </div>
    </section>
  )
}
