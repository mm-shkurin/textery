import { TEXT_STYLE_OPTIONS, type GenerationParameters } from '../utils/generationParameters'
import composerStyles from './Composer.module.css'

interface ComposerStyleProps {
  parameters: GenerationParameters
  onChange: (parameters: GenerationParameters) => void
}

const STYLE_LABEL_ID = 'composer-style-label'

/**
 * «Выбрать стиль текста» — научный / публицистический / художественный.
 *
 * A real `<select>` with a placeholder option rather than three chips: the register is one choice
 * out of a closed set, which is exactly what the element means, and it stays reachable by keyboard
 * and announced by a screen reader without any of it being rebuilt here.
 *
 * The placeholder is a genuine value, not a prompt to be dismissed — «Не указан» sends no style at
 * all and lets the model pick its own register, which is what every generation made before this
 * picker existed got. Preselecting «Научный» would silently record a choice nobody made.
 */
export function ComposerStyle({ parameters, onChange }: ComposerStyleProps) {
  const selected = TEXT_STYLE_OPTIONS.find((option) => option.value === parameters.textStyle)

  return (
    <div className={`${composerStyles['composer-field']} composer-field-style`}>
      <span id={STYLE_LABEL_ID} className={composerStyles['composer-field-label']}>
        Стиль текста
      </span>
      <select
        className={`${composerStyles['composer-field-input']} ${composerStyles['composer-style-select']}`}
        data-testid="style-select"
        aria-labelledby={STYLE_LABEL_ID}
        value={parameters.textStyle}
        onChange={(event) =>
          onChange({
            ...parameters,
            // The cast is safe by construction: every non-empty option below is rendered from
            // TEXT_STYLES, so the only values this element can report are '' and a TextStyle.
            textStyle: event.target.value as GenerationParameters['textStyle'],
          })
        }
      >
        <option value="">Не указан</option>
        {TEXT_STYLE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {/* The chosen register's one-line description, under the control. The labels alone leave a
          user guessing at the difference between публицистический and художественный, and the
          hint is the only place that difference is stated. */}
      {selected !== undefined && (
        <span className={composerStyles['composer-style-hint']} data-testid="style-hint">
          {selected.hint}
        </span>
      )}
    </div>
  )
}
