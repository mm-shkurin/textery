import { suggestionsFor } from '../utils/topicSuggestions'
import type { DocumentType } from '../../../shared/documentTypes'
import styles from './TopicSuggestions.module.css'

interface TopicSuggestionsProps {
  documentType: DocumentType
  onPick: (topic: string) => void
  // Hidden once the user has written something of their own: the examples are a way INTO the
  // field, and a click that replaces text someone just typed is a destructive surprise from a
  // control that looks like a hint.
  isVisible: boolean
}

/**
 * «Примеры запросов» — clickable topics under the composer's topic field.
 *
 * Real buttons, not decorative pills: their whole purpose is to be pressed, and a `<div>` with an
 * onClick is unreachable by keyboard and announced as nothing.
 */
export function TopicSuggestions({ documentType, onPick, isVisible }: TopicSuggestionsProps) {
  const suggestions = suggestionsFor(documentType)
  if (!isVisible || suggestions.length === 0) return null

  return (
    <div className={styles['topic-suggestions']} data-testid="topic-suggestions">
      <span className={styles['topic-suggestions-label']}>Например:</span>
      <ul className={styles['topic-suggestions-list']}>
        {suggestions.map((suggestion) => (
          <li key={suggestion}>
            <button
              type="button"
              className={styles['topic-suggestion']}
              data-testid="topic-suggestion"
              onClick={() => onPick(suggestion)}
            >
              {suggestion}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
