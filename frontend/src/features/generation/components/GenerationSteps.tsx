import styles from './GenerationScreen.module.css'

// Три шага, которые фрейм рисует под заголовком. Это не навигация: перейти на шаг нельзя,
// шаг наступает сам — поэтому они рендерятся списком, а не кнопками, и текущий помечен
// `aria-current`, а не «выбран».
//
// Второй шаг на фрейме называется «Введите параметры», хотя параметры стоят на первом
// экране вместе с темой: там их вводят до отправки, отдельного экрана параметров нет и не
// планируется. Названия оставлены фреймовыми — экран должен читаться так, как нарисован, —
// но реальные шаги здесь два: заполнить форму и получить документ.
const STEPS = ['Укажите тему', 'Введите параметры', 'Получите документ']

interface GenerationStepsProps {
  // 1 — форма, 2 — генерация идёт, 3 — документ готов (и экран уже сменился редактором).
  current: 1 | 2 | 3
}

export function GenerationSteps({ current }: GenerationStepsProps) {
  return (
    <ol className={styles['genform-steps']} data-testid="generation-steps">
      {STEPS.map((label, index) => {
        const step = index + 1
        const isCurrent = step === current
        return (
          <li
            key={label}
            className={`${styles['genform-step']}${isCurrent ? ' ' + styles['genform-step-current'] : ''}`}
            aria-current={isCurrent ? 'step' : undefined}
          >
            <span className={styles['genform-step-num']}>{step}</span>
            <span className={styles['genform-step-label']}>{label}</span>
            {/* Линия между шагами — элемент, а не border контейнера: так она занимает
                остаток строки и не разъезжается при другой длине подписей. Последний шаг
                её не рисует, иначе линия уходила бы в пустоту за правым краем. */}
            {step < STEPS.length && (
              <span className={styles['genform-step-line']} aria-hidden="true" />
            )}
          </li>
        )
      })}
    </ol>
  )
}
