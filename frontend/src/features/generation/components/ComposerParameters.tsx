import { ComposerStyle } from './ComposerStyle'
import {
  MAX_EXTRA_WISHES_LENGTH,
  MAX_REQUIREMENTS_LENGTH,
  MAX_VOLUME_PAGES,
  MIN_VOLUME_PAGES,
  type GenerationParameters,
} from '../utils/generationParameters'
import composerStyles from './Composer.module.css'

interface ComposerParametersProps {
  parameters: GenerationParameters
  onChange: (parameters: GenerationParameters) => void
}

const REQUIREMENTS_LABEL_ID = 'composer-requirements-label'
const VOLUME_LABEL_ID = 'composer-volume-label'
const WISHES_LABEL_ID = 'composer-wishes-label'

/**
 * The three fields beside the topic: требования, объём, дополнительные пожелания.
 *
 * They are drawn in `mockups/desktop/04-generation-form.html` and were never built — the client
 * sent a hardcoded 5 pages and nothing else, so a user could not say how long the work should be
 * or what it had to contain. Split out of `Composer` to keep both files under the 200-line cap.
 *
 * Labels are associated by id rather than by wrapping `<label>`, matching `Composer`'s topic
 * heading: the visible text stays the single source of each field's accessible name.
 */
export function ComposerParameters({ parameters, onChange }: ComposerParametersProps) {
  const set = (patch: Partial<GenerationParameters>) => onChange({ ...parameters, ...patch })

  return (
    <div className={composerStyles['composer-parameters']}>
      <div className={composerStyles['composer-parameters-row']}>
        <div
          className={`${composerStyles['composer-field']} ${composerStyles['composer-field-grow']}`}
        >
          <span id={REQUIREMENTS_LABEL_ID} className={composerStyles['composer-field-label']}>
            Требования
          </span>
          <textarea
            className={composerStyles['composer-field-input']}
            data-testid="requirements-input"
            aria-labelledby={REQUIREMENTS_LABEL_ID}
            placeholder="Например: официально-деловой стиль, ссылки на источники"
            value={parameters.requirements}
            // The domain's own cap. Stopping the keystroke is a better answer than a 400 after
            // the user has written three thousand characters.
            maxLength={MAX_REQUIREMENTS_LENGTH}
            rows={2}
            onChange={(e) => set({ requirements: e.target.value })}
          />
        </div>

        <div
          className={`${composerStyles['composer-field']} ${composerStyles['composer-field-volume']}`}
        >
          <span
            id={VOLUME_LABEL_ID}
            className={`${composerStyles['composer-field-label']} ${composerStyles.required}`}
          >
            Объём, страниц
            <span className={composerStyles['composer-required-marker']} aria-hidden="true">
              {' *'}
            </span>
          </span>
          <input
            type="number"
            className={composerStyles['composer-field-input']}
            data-testid="volume-input"
            aria-labelledby={VOLUME_LABEL_ID}
            min={MIN_VOLUME_PAGES}
            max={MAX_VOLUME_PAGES}
            required
            value={parameters.volumePages}
            onChange={(e) => {
              // A cleared number input reports '' — `Number('')` is 0, which would silently send
              // a volume the server refuses. NaN is carried instead, so the send button's own
              // range check is what decides, in one place, whether the form may be submitted.
              const raw = e.target.value
              set({ volumePages: raw === '' ? Number.NaN : Number(raw) })
            }}
          />
        </div>
      </div>

      <ComposerStyle parameters={parameters} onChange={onChange} />

      <div className={composerStyles['composer-field']}>
        <span id={WISHES_LABEL_ID} className={composerStyles['composer-field-label']}>
          Дополнительные пожелания
        </span>
        <textarea
          className={composerStyles['composer-field-input']}
          data-testid="wishes-input"
          aria-labelledby={WISHES_LABEL_ID}
          placeholder="Что-то ещё, что стоит учесть при генерации"
          value={parameters.extraWishes}
          maxLength={MAX_EXTRA_WISHES_LENGTH}
          rows={2}
          onChange={(e) => set({ extraWishes: e.target.value })}
        />
      </div>
    </div>
  )
}
