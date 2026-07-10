import ReactMarkdown from 'react-markdown'
import type { GenerationUiState } from '../hooks/useGeneration'

interface DocAreaProps {
  state: GenerationUiState
  content: string | null
  volumePages: number | null
  error: string | null
  label: string
  onReset: () => void
}

export function DocArea({ state, content, volumePages, error, label, onReset }: DocAreaProps) {
  if (state === 'completed') {
    return (
      <div className="doc-content">
        <div className="doc-meta">
          {label} · {volumePages ?? '—'} страниц · создан только что
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
