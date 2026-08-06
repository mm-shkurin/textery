import './ChatButton.css'
import './Composer.css'
import { ComposerParameters } from './ComposerParameters'
import { isVolumeAcceptable, type GenerationParameters } from '../generationParameters'

export const MAX_TOPIC_LENGTH = 500

interface ComposerProps {
  // Built by the caller from the picked type ('Тема доклада', 'Тема реферата'). Mockup 04 could
  // hardcode 'Тема доклада' because a mockup depicts one type; this heading sits directly under a
  // breadcrumb naming the real one, so a literal here would name a different type than the chip.
  topicLabel: string
  topic: string
  setTopic: (v: string) => void
  parameters: GenerationParameters
  setParameters: (parameters: GenerationParameters) => void
  onSend: () => void
}

const TOPIC_LABEL_ID = 'composer-topic-label'

export function Composer({
  topicLabel,
  topic,
  setTopic,
  parameters,
  setParameters,
  onSend,
}: ComposerProps) {
  return (
    <div className="composer">
      {/* Associated, not merely adjacent: the heading sat right above the field and named it to
          anyone who could see them together, while a screen reader announced an unlabelled text
          box. aria-labelledby rather than a <label> so the visible heading stays the one source
          of the name — a <label> here would either duplicate the text or replace the h3 and
          change the page's outline. */}
      <h3 id={TOPIC_LABEL_ID} className="required">
        {topicLabel}
        {/* The required marker is markup, not a `::after` on the heading: this h3 IS the
            textarea's accessible name, and a real browser folds CSS-generated content into the
            name computation — so the styling-only asterisk would rename the field to
            'Тема доклада *' in every screen reader, a divergence jsdom (which applies no CSS)
            can never catch. aria-hidden keeps it decorative; `required` on the field itself is
            what conveys the constraint. */}
        <span className="composer-required-marker" aria-hidden="true">
          {' *'}
        </span>
      </h3>
      <textarea
        className="composer-input"
        data-testid="topic-input"
        aria-labelledby={TOPIC_LABEL_ID}
        placeholder="Например: Влияние искусственного интеллекта на образование"
        value={topic}
        maxLength={MAX_TOPIC_LENGTH}
        onChange={(e) => setTopic(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) onSend()
        }}
        rows={4}
      />
      <ComposerParameters parameters={parameters} onChange={setParameters} />
      {/* Both required fields gate the button, not the topic alone. A volume outside 1..10 — or
          an emptied number input, which reports NaN — would otherwise be refused by the server
          with a 400 the user cannot act on from this screen. */}
      <button
        type="button"
        className="cw-btn cw-btn-primary composer-send"
        data-testid="topic-send"
        onClick={onSend}
        disabled={!topic.trim() || !isVolumeAcceptable(parameters.volumePages)}
      >
        Сгенерировать
      </button>
      {/* Mockup 04's submit-row hint: the wait is long enough that the user needs to be told
          up front, not only once the pending screen replaces this one. */}
      <p className="composer-hint">Обычно занимает 1–2 минуты</p>
    </div>
  )
}
