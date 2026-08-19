import './LandingSection.css'
import './LandingProcess.css'

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
    <section className="landing-section" data-testid="landing-process">
      <div className="landing-section-head">
        <span className="landing-eyebrow">Процесс</span>
        <h2 className="landing-section-title">
          Простой рабочий процесс. Максимальная автоматизация и минимум усилий
        </h2>
        <p className="landing-section-lead">
          От темы до готового документа — три шага без лишних действий
        </p>
      </div>

      <ol className="landing-section-body process-steps">
        {STEPS.map((step, index) => (
          <li className="process-card" key={step.title}>
            <div className="process-well" aria-hidden="true">
              <span className="process-step-number">{index + 1}</span>
            </div>
            <h3 className="process-title">{step.title}</h3>
            <p className="process-text">{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
