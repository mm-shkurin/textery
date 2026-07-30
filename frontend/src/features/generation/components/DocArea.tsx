import ReactMarkdown from 'react-markdown'
import './ChatButton.css'
import type { GenerationUiState } from '../hooks/useGeneration'
import { formatRelativeTime } from '../formatRelativeTime'
import {
  generatingTitle,
  generationFailedTitle,
  topicPromptTitle,
  type DocumentType,
} from '../../../shared/documentTypes'

interface DocAreaProps {
  state: GenerationUiState
  content: string | null
  volumePages: number | null
  error: string | null
  // The id and its label, the pair ChatWorkspace already carries: `label` is the breadcrumb-style
  // display form, while copy that names the type inside a sentence has to decline it, which only
  // the id can look up.
  documentType: DocumentType
  label: string
  createdAt: string | null
  onReset: () => void
}

export function DocArea({
  state,
  content,
  volumePages,
  error,
  documentType,
  label,
  createdAt,
  onReset,
}: DocAreaProps) {
  if (state === 'completed') {
    return (
      <div className="doc-content">
        <div className="doc-meta">
          {label} · {volumePages ?? '—'} страниц · {formatRelativeTime(createdAt)}
        </div>
        <div className="doc-body markdown-body" data-testid="doc-body">
          <ReactMarkdown>{content ?? ''}</ReactMarkdown>
        </div>
        <div className="actions-row">
          <button
            type="button"
            className="cw-btn cw-btn-primary"
            data-testid="doc-reset"
            onClick={onReset}
          >
            Создать новый доклад
          </button>
        </div>
      </div>
    )
  }
  if (state === 'failed') {
    return (
      <div className="doc-placeholder" data-testid="doc-error">
        <div className="icon-circle">✕</div>
        <h2>{generationFailedTitle(documentType)}</h2>
        <p>{error ?? 'Попробуйте создать новый запрос — измените тему или требования.'}</p>
        <button
          type="button"
          className="cw-btn cw-btn-primary"
          data-testid="error-reset"
          onClick={onReset}
        >
          Создать новый запрос
        </button>
      </div>
    )
  }
  if (state === 'pending') {
    // Story 18 contract: the generating surface is marked with this testid (also scenario 1.2's
    // subject). It is present only while a generation is in flight, so a Selenium wait on it
    // observes exactly the generating state and nothing else.
    return (
      <div className="doc-placeholder" data-testid="generation-generating">
        <div className="spinner" />
        <h2>{generatingTitle(documentType)}</h2>
        <p>Обычно занимает 1–2 минуты — страница обновится автоматически</p>
      </div>
    )
  }
  return (
    <div className="doc-placeholder">
      <h2>{topicPromptTitle(documentType)}</h2>
      <p>Введите тему в панели слева — ИИ сгенерирует готовый текст.</p>
    </div>
  )
}
