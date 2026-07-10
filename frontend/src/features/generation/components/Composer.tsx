export const MAX_TOPIC_LENGTH = 500

interface ComposerProps {
  topic: string
  setTopic: (v: string) => void
  onSend: () => void
}

export function Composer({ topic, setTopic, onSend }: ComposerProps) {
  return (
    <div className="composer">
      <h3>Тема доклада</h3>
      <textarea
        className="composer-input"
        data-testid="topic-input"
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
