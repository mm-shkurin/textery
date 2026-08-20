import styles from './LandingStats.module.css'

// Figma `Desktop` (node 90:880), the three 386x213 cards at y=668. Each carries a stacked
// avatar cluster straddling its top edge; the icon glyph on the front chip differs per card.
const STATS = [
  {
    value: '1 млн+',
    text: 'Профессиональных презентаций создано',
    icon: '🌐',
  },
  {
    value: '4 сек',
    text: 'Среднее время генерации доклада, реферата, эссе, сочинения',
    icon: '⏱',
  },
  {
    value: 'Word и PDF',
    text: 'Экспорт в Word и PDF без сжатия и искажений',
    icon: '⤓',
  },
]

export function LandingStats() {
  return (
    <section className={styles.stats} data-testid="landing-stats">
      {STATS.map((stat) => (
        <article className={styles['stat-card']} key={stat.value}>
          <div className={styles['stat-chips']} aria-hidden="true">
            <span className={styles['stat-chip'] + ' ' + styles['stat-chip-back']} />
            <span className={styles['stat-chip'] + ' ' + styles['stat-chip-mid']} />
            <span className={styles['stat-chip'] + ' ' + styles['stat-chip-front']}>
              {stat.icon}
            </span>
          </div>
          <p className={styles['stat-value']}>{stat.value}</p>
          <p className={styles['stat-text']}>{stat.text}</p>
        </article>
      ))}
    </section>
  )
}
