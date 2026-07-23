import './LandingStats.css'

// Figma `Desktop` (node 90:880), the three 315x174 cards at y=504. Each carries a stacked
// avatar cluster above the figure; the icon glyph on the front chip differs per card.
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
    <section className="stats" data-testid="landing-stats">
      {STATS.map((stat) => (
        <article className="stat-card" key={stat.value}>
          <div className="stat-chips" aria-hidden="true">
            <span className="stat-chip stat-chip-back" />
            <span className="stat-chip stat-chip-mid" />
            <span className="stat-chip stat-chip-front">{stat.icon}</span>
          </div>
          <p className="stat-value">{stat.value}</p>
          <p className="stat-text">{stat.text}</p>
        </article>
      ))}
    </section>
  )
}
