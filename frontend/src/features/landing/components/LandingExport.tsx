import landingSectionStyles from './LandingSection.module.css'
import { LandingSectionHead } from './LandingSectionHead'
import styles from './LandingExport.module.css'

// Figma `Desktop` → `Export` (node 1097:10952): the section that shows what leaves the product.
// Two cards side by side — ours at 98% and Word's at 72% — each holding the frame's render of the
// same document after export, then three numbers under them.
//
// The renders are exported from the frame rather than rebuilt in markup. They are a drawing OF a
// document editor (selection handles, a font dropdown, checkmarks against a checkerboard), not a
// piece of this product's UI: rebuilding them would mean maintaining a fake editor in CSS whose
// only job is to be a picture.
const CARDS = [
  {
    chip: 'Textery AI',
    verdict: 'Идеально',
    verdictKind: 'ok' as const,
    score: '98%',
    shot: '/design/landing/export-textery.png',
  },
  {
    chip: 'Word',
    verdict: 'Сломано',
    verdictKind: 'bad' as const,
    score: '72%',
    shot: '/design/landing/export-word.png',
  },
]

// The gradient discs the frame sets beside the closing numbers, ending in the round «try it free»
// badge. Decorative. The fifth render is the one the quality bars are also filled with — the frame
// reuses it here, and so does this.
const DISCS = [
  '/design/landing/export-circle-1.webp',
  '/design/landing/export-circle-2.webp',
  '/design/landing/quality-bar-teal.webp',
  '/design/landing/export-circle-3.webp',
  '/design/landing/export-circle-4.webp',
]

export function LandingExport() {
  return (
    <section className={landingSectionStyles['landing-section']} data-testid="landing-export">
      <LandingSectionHead
        eyebrow="Без правок"
        title={
          <>
            <span className={landingSectionStyles['landing-section-title-accent']}>
              Идеальный экспорт
            </span>
            <br />в Word и PDF
          </>
        }
        lead={
          <>
            <strong>98% точность</strong> — без потери форматирования, шрифтов
          </>
        }
      />

      <div className={`${landingSectionStyles['landing-section-body']} ${styles['export-cards']}`}>
        {CARDS.map((card) => (
          <article
            className={`${styles['export-card']}${card.verdictKind === 'bad' ? ' ' + styles['export-card-rival'] : ''}`}
            key={card.chip}
          >
            <div className={styles['export-head']}>
              <div className={styles['export-chips']}>
                <span className={`${styles['export-chip']} ${styles['export-chip-brand']}`}>
                  {card.chip}
                </span>
                <span
                  className={`${styles['export-chip']} ${styles[`export-chip-${card.verdictKind}`]}`}
                >
                  {card.verdict}
                </span>
              </div>
              <p className={styles['export-score']}>
                <b>{card.score}</b>
                <span>точность</span>
              </p>
            </div>

            {/* Not lazy: these two renders ARE the section's argument, and a placeholder that
                fills in after the reader has scrolled past leaves two empty cards behind. */}
            <img className={styles['export-shot']} src={card.shot} alt="" decoding="async" />
          </article>
        ))}
      </div>

      <div className={styles['export-summary']}>
        <div className={styles['export-summary-left']}>
          <p className={styles['export-stat']}>
            <b>98%</b>
            <span>Точность позиционирования текста</span>
          </p>
          <p className={styles['export-note']}>
            <strong>Экспорт без потерь.</strong> Текстовый документ сохраняет исходную вёрстку,
            шрифты и другие элементы.
          </p>
        </div>

        <div className={styles['export-summary-right']}>
          <div className={styles['export-discs']} aria-hidden="true">
            {DISCS.map((disc) => (
              <img src={disc} alt="" key={disc} />
            ))}
            <span className={styles['export-badge']}>↗</span>
          </div>

          <div className={styles['export-stats-row']}>
            <p className={styles['export-stat']}>
              <b>100%</b>
              <span>Сохранение ваших шрифтов</span>
            </p>
            <p className={styles['export-stat']}>
              <b>0</b>
              <span>Потерянных элементов файла</span>
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
