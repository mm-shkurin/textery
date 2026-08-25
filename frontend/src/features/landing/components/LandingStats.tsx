import styles from './LandingStats.module.css'

// Figma `Desktop` (node 1362:8224), the three 386x213 glass cards at y=668. Each carries a stacked
// avatar cluster straddling its top edge: two of the frame's gradient renders behind a black chip
// with the card's own glyph on it.
//
// The avatars are the frame's artwork, not flat blue discs. They were drawn as `--blue-200` /
// `--blue-500` here, which turned three distinct clusters into one repeated pair of dots, and on
// the hero — where the glass and the gradients are the whole visual argument — that read as a
// placeholder nobody had finished.
const STATS = [
  {
    value: '1 млн+',
    // The frame's own words. «Профессиональных презентаций создано» was left over from the
    // template this page grew out of: the product makes documents, and the one number a visitor
    // reads first should not name the wrong artefact.
    text: (
      <>
        <strong>Профессиональных Word документов</strong> создано с помощью Textery AI
      </>
    ),
    avatars: ['hero-stat-avatar-1', 'hero-stat-avatar-2'],
    icon: '🌐',
  },
  {
    value: '4 сек',
    text: (
      <>
        <strong>Среднее время</strong> генерации доклада, реферата, эссе, сочинения
      </>
    ),
    avatars: ['hero-stat-avatar-3', 'hero-stat-avatar-2'],
    icon: '⏱',
  },
  {
    value: 'Word и PDF',
    text: (
      <>
        <strong>Экспорт в Word и PDF</strong> без сжатия и искажений
      </>
    ),
    avatars: ['hero-stat-avatar-3', 'hero-stat-avatar-4'],
    icon: '⤓',
  },
]

export function LandingStats() {
  return (
    <section className={styles.stats} data-testid="landing-stats">
      {STATS.map((stat) => (
        <article className={styles['stat-card']} key={stat.value}>
          <div className={styles['stat-chips']} aria-hidden="true">
            {stat.avatars.map((avatar, index) => (
              <img
                className={styles['stat-chip']}
                key={avatar + String(index)}
                src={`/design/landing/${avatar}.webp`}
                alt=""
                decoding="async"
              />
            ))}
            <span className={`${styles['stat-chip']} ${styles['stat-chip-front']}`}>
              {stat.icon}
            </span>
          </div>
          <p className={styles['stat-value']}>{stat.value}</p>
          <p className={styles['stat-text']}>{stat.text}</p>
        </article>
      ))}

      <img
        className={`${styles['stat-sparkle']} ${styles['stat-sparkle-left']}`}
        src="/design/landing/hero-sparkle.webp"
        alt=""
        aria-hidden="true"
        decoding="async"
      />
      <img
        className={`${styles['stat-sparkle']} ${styles['stat-sparkle-right']}`}
        src="/design/landing/hero-sparkle.webp"
        alt=""
        aria-hidden="true"
        decoding="async"
      />
    </section>
  )
}
