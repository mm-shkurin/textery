import landingSectionStyles from './LandingSection.module.css'
import { LandingSectionHead } from './LandingSectionHead'
import styles from './LandingProcess.module.css'

// Figma `Desktop` → `Process` (node 1337:7098): three 462x397 cards in a row, each a white panel
// at a 24px radius holding a recessed 438x240 well over a 24/29 step name and its 18/22 line.
//
// Numbered here, unnumbered in the frame: the section's own lead calls them «три шага», and the
// order is the whole point of the section — on a phone, where the three stack, nothing else says
// which comes first.
//
// The well holds the frame's own render of the step — the create form, the spinner, the editor
// with its toolbar. A numbered empty box said «a picture goes here»; these three ARE the picture,
// and they are what makes the section answer «what will this look like» rather than «what are the
// steps called».
const STEPS = [
  {
    title: 'Опишите задачу',
    text: 'Укажите тему, тип работы, объём и требования',
    shot: '/design/landing/process-step-1.png',
  },
  {
    title: 'Получите готовый текст',
    text: 'ИИ сгенерирует структурированный документ за 30 секунд',
    shot: '/design/landing/process-step-2.png',
  },
  {
    title: 'Отредактируйте и скачайте',
    text: 'Доработайте текст во встроенном редакторе и скачайте в Word или PDF',
    shot: '/design/landing/process-step-3.png',
  },
]

export function LandingProcess() {
  return (
    <section className={landingSectionStyles['landing-section']} data-testid="landing-process">
      <LandingSectionHead
        eyebrow="Процесс"
        title={
          <>
            {/* The frame paints the first line blue and the second in ink — two claims, not one
                sentence: what the process IS, then what it gives you. */}
            <span className={landingSectionStyles['landing-section-title-accent']}>
              Простой рабочий процесс
            </span>
            <br />
            Максимальная автоматизация и минимум усилий
          </>
        }
        lead="От темы до готового документа — три шага без лишних действий"
      />

      <ol className={`${landingSectionStyles['landing-section-body']} ${styles['process-steps']}`}>
        {STEPS.map((step) => (
          <li className={styles['process-card']} key={step.title}>
            <div className={styles['process-well']}>
              <img src={step.shot} alt="" decoding="async" loading="lazy" />
            </div>
            <h3 className={styles['process-title']}>{step.title}</h3>
            <p className={styles['process-text']}>{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
