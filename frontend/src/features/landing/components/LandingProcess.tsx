import landingSectionStyles from './LandingSection.module.css'
import styles from './LandingProcess.module.css'

// Figma `Desktop` → `Process` (node 1337:7098): three 462x397 cards in a row, each a white panel
// at a 24px radius holding a recessed 438x240 well over a 24/29 step name and its 18/22 line.
//
// Numbered here, unnumbered in the frame: the section's own lead calls them «три шага», and the
// order is the whole point of the section — on a phone, where the three stack, nothing else says
// which comes first.
const STEPS = [
  { title: 'Опишите задачу', text: 'Укажите тему, тип работы, объём и требования' },
  {
    title: 'Получите готовый текст',
    text: 'ИИ сгенерирует структурированный документ за 30 секунд',
  },
  {
    title: 'Отредактируйте и скачайте',
    text: 'Доработайте текст во встроенном редакторе и скачайте в Word или PDF',
  },
]

export function LandingProcess() {
  return (
    <section className={landingSectionStyles['landing-section']} data-testid="landing-process">
      <div className={landingSectionStyles['landing-section-head']}>
        <span className={landingSectionStyles['landing-eyebrow']}>Процесс</span>
        <h2 className={landingSectionStyles['landing-section-title']}>
          Простой рабочий процесс. Максимальная автоматизация и минимум усилий
        </h2>
        <p className={landingSectionStyles['landing-section-lead']}>
          От темы до готового документа — три шага без лишних действий
        </p>
      </div>

      <ol className={`${landingSectionStyles['landing-section-body']} ${styles['process-steps']}`}>
        {STEPS.map((step, index) => (
          <li className={styles['process-card']} key={step.title}>
            <div className={styles['process-well']} aria-hidden="true">
              <span className={styles['process-step-number']}>{index + 1}</span>
            </div>
            <h3 className={styles['process-title']}>{step.title}</h3>
            <p className={styles['process-text']}>{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
