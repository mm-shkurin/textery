import { LandingSection, AccentLine } from './LandingSection'
import { LandingCtaButton } from './LandingCtaButton'
import type { CSSProperties } from 'react'

import styles from './LandingShowcase.module.css'
import landingSectionStyles from './LandingSection.module.css'
import { LandingSectionHead } from './LandingSectionHead'

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
//
// `art` names the gradient render the frame fills each bar with (node 1417:17932 and its
// siblings): three different gradients, one per quality, reused down both columns so a row reads
// as one measurement seen twice. A flat blue fill — what this drew before — turned six bars into
// six identical blue pills and lost the only thing that tied «97%» to the «61%» beside it.
const SCORES = [
  {
    engine: 'Textery',
    ours: true,
    metrics: [
      {
        art: 'quality-bar-teal',
        score: 97,
        title: 'Точность терминов',
        text: 'Использует корректную деловую лексику без англицизмов и дословных переводов',
      },
      {
        art: 'quality-bar-magenta',
        score: 92,
        title: 'Естественный стиль речи',
        text: 'Textery AI изначально обучена понимать и генерировать на русском языке',
      },
      {
        art: 'quality-bar-violet',
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
        art: 'quality-bar-teal',
        score: 61,
        title: 'Точность терминов',
        text: 'Не адаптируют лексику под русскоязычную аудиторию, подставляя английские термины',
      },
      {
        art: 'quality-bar-magenta',
        score: 56,
        title: 'Естественный стиль речи',
        text: 'Обучены на английском языке и переводят русский текст, теряя смысл и контекст',
      },
      {
        art: 'quality-bar-violet',
        score: 47,
        title: 'Сохранение контекста',
        text: 'Упрощают или искажают исходную задачу, теряя второстепенные и ключевые смыслы',
      },
    ],
  },
]

export function LandingShowcase({ onPrimaryCtaClick }: LandingShowcaseProps) {
  return (
    <LandingSection testId="landing-showcase">
      <LandingSectionHead
        eyebrow="Преимущества"
        title={
          <>
            <AccentLine>Лучшее качество</AccentLine>
            <br />
            на русском языке
          </>
        }
        lead={
          <>
            <strong>Нативная поддержка русского vs автоперевод</strong> конкурентов. Сравнение
            генерации одного промпта
          </>
        }
      />

      <div
        className={`${landingSectionStyles['landing-section-body']} ${styles['showcase-panel']}`}
      >
        {SCORES.map((column) => (
          <article className={styles['showcase-card']} key={column.engine}>
            {/* Our own column wears the wordmark, the other a plain label — the frame's way of
                saying which of the two is the product without colouring the numbers. */}
            <p className={styles['showcase-chip']}>
              {column.ours && (
                <img
                  className={styles['showcase-chip-logo']}
                  src="/design/logo-textery.svg"
                  alt=""
                  aria-hidden="true"
                />
              )}
              {/* The wordmark artwork already carries the name, so the label is only rendered
                  for the column that has no mark. */}
              {column.ours ? null : column.engine}
            </p>
            {column.metrics.map((metric) => (
              <div className={styles['showcase-metric']} key={metric.title}>
                <div className={styles['showcase-scale']} aria-hidden="true">
                  <span>0%</span>
                  <span>100%</span>
                </div>
                {/* A real <progress>: the number beside it is the same value, and a bar drawn
                    with two <div>s tells an assistive technology nothing about what it fills. */}
                <progress
                  className={styles['showcase-bar']}
                  style={
                    { '--bar-art': `url('/design/landing/${metric.art}.webp')` } as CSSProperties
                  }
                  value={metric.score}
                  max={100}
                >
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

      <LandingCtaButton
        onClick={onPrimaryCtaClick}
        wrapperClassName={styles['showcase-action']}
        testId="features-primary-cta-button"
        label="Создать генерацию"
      />
    </LandingSection>
  )
}
