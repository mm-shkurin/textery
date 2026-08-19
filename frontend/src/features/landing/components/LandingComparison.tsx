import './LandingSection.css'
import './LandingComparison.css'

// Figma `Desktop` → `Comparison` (node 1358:7627): a dark #161616 band carrying a 1160px table —
// a header row of three 380px columns, then four rows separated by hairlines.
//
// A real <table>: the section IS a comparison of two products across four features, and a grid of
// <div>s would leave a screen-reader user hearing twelve loose values with nothing tying each to
// its row or its column.
const ROWS = [
  { feature: '🚀 Скорость генерации', textery: '30 секунд', others: '~ 67 секунд' },
  { feature: '🇷🇺 Поддержка русского языка', textery: 'Нативная', others: 'Автоперевод' },
  { feature: '🗂 Точность экспорта Word', textery: '98%', others: '~ 74%' },
  { feature: '📍 Работа из России', textery: 'Без VPN', others: 'Нужен VPN' },
]

interface LandingComparisonProps {
  onPrimaryCtaClick?: () => void
}

export function LandingComparison({ onPrimaryCtaClick }: LandingComparisonProps) {
  return (
    <section className="comparison" data-testid="landing-comparison">
      <div className="landing-section comparison-inner">
        <div className="landing-section-head">
          <span className="landing-eyebrow comparison-eyebrow">Сравните сами</span>
          <h2 className="landing-section-title comparison-title">Почему выбирают Textery AI</h2>
          <p className="landing-section-lead comparison-lead">
            Честное сравнение с главными конкурентами на рынке AI-генерации текстов
          </p>
        </div>

        <table className="landing-section-body comparison-table">
          <thead>
            <tr>
              <th scope="col">Возможность</th>
              <th scope="col">
                <span className="comparison-chip comparison-chip-ours">Textery AI</span>
              </th>
              <th scope="col">
                <span className="comparison-chip">Другие ИИ</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.feature}>
                <th scope="row">{row.feature}</th>
                <td className="comparison-ours">{row.textery}</td>
                <td>{row.others}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {onPrimaryCtaClick !== undefined && (
          <div className="comparison-action">
            <button
              type="button"
              className="btn-light"
              data-testid="comparison-primary-cta"
              onClick={onPrimaryCtaClick}
            >
              Попробовать бесплатно
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
