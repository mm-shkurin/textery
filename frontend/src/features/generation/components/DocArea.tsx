import ReactMarkdown from 'react-markdown'
import type { GenerationUiState } from '../hooks/useGeneration'
import { formatRelativeTime } from '../formatRelativeTime'

interface DocAreaProps {
  state: GenerationUiState
  content: string | null
  volumePages: number | null
  error: string | null
  label: string
  createdAt: string | null
  onReset: () => void
}

export function DocArea({
  state,
  content,
  volumePages,
  error,
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
          <button type="button" className="cw-btn cw-btn-primary" onClick={onReset}>
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
        <h2>Не удалось сгенерировать доклад</h2>
        <p>{error ?? 'Попробуйте создать новый запрос — измените тему или требования.'}</p>
        <button type="button" className="cw-btn cw-btn-primary" onClick={onReset}>
          Создать новый запрос
        </button>
      </div>
    )
  }
  if (state === 'pending') {
    return (
      <div className="doc-placeholder">
        <div className="spinner" />
        <h2>Готовим ваш доклад</h2>
        <p>Обычно занимает 1–2 минуты — страница обновится автоматически</p>
      </div>
    )
  }
  return (
    <div className="doc-placeholder">
      <h2>Опишите тему доклада</h2>
      <p>Введите тему в панели слева — ИИ сгенерирует готовый текст.</p>
    </div>
  )
}
