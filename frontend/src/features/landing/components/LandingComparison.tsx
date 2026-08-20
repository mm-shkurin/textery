import landingSectionStyles from './LandingSection.module.css'
import styles from './LandingComparison.module.css'
import navbarButtonsStyles from '../../../shared/components/navbar/NavbarButtons.module.css'

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
    <section className={styles.comparison} data-testid="landing-comparison">
      <div className={`${landingSectionStyles['landing-section']} ${styles['comparison-inner']}`}>
        <div className={landingSectionStyles['landing-section-head']}>
          <span
            className={`${landingSectionStyles['landing-eyebrow']} ${styles['comparison-eyebrow']}`}
          >
            Сравните сами
          </span>
          <h2
            className={`${landingSectionStyles['landing-section-title']} ${styles['comparison-title']}`}
          >
            Почему выбирают Textery AI
          </h2>
          <p
            className={`${landingSectionStyles['landing-section-lead']} ${styles['comparison-lead']}`}
          >
            Честное сравнение с главными конкурентами на рынке AI-генерации текстов
          </p>
        </div>

        <table
          className={`${landingSectionStyles['landing-section-body']} ${styles['comparison-table']}`}
        >
          <thead>
            <tr>
              <th scope="col">Возможность</th>
              <th scope="col">
                <span className={`${styles['comparison-chip']} ${styles['comparison-chip-ours']}`}>
                  Textery AI
                </span>
              </th>
              <th scope="col">
                <span className={styles['comparison-chip']}>Другие ИИ</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.feature}>
                <th scope="row">{row.feature}</th>
                <td className={styles['comparison-ours']}>{row.textery}</td>
                <td>{row.others}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {onPrimaryCtaClick !== undefined && (
          <div className={styles['comparison-action']}>
            <button
              type="button"
              className={navbarButtonsStyles['btn-light']}
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
