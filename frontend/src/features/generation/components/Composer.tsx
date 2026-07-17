export const MAX_TOPIC_LENGTH = 500

interface ComposerProps {
  topic: string
  setTopic: (v: string) => void
  onSend: () => void
}

const TOPIC_LABEL_ID = 'composer-topic-label'

export function Composer({ topic, setTopic, onSend }: ComposerProps) {
  return (
    <div className="composer">
      {/* Associated, not merely adjacent: the heading sat right above the field and named it to
          anyone who could see them together, while a screen reader announced an unlabelled text
          box. aria-labelledby rather than a <label> so the visible heading stays the one source
          of the name — a <label> here would either duplicate the text or replace the h3 and
          change the page's outline. */}
      <h3 id={TOPIC_LABEL_ID}>Тема доклада</h3>
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
      <button
        type="button"
        className="cw-btn cw-btn-primary composer-send"
        data-testid="topic-send"
        onClick={onSend}
        disabled={!topic.trim()}
      >
        Сгенерировать
      </button>
    </div>
  )
}
