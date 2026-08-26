import ReactMarkdown from 'react-markdown'
import chatButtonStyles from './ChatButton.module.css'
import chatWorkspaceDocStyles from './ChatWorkspaceDoc.module.css'
import docMarkdownStyles from './DocMarkdown.module.css'
import type { GenerationUiState } from '../hooks/useGeneration'
import { formatRelativeTime } from '../utils/formatRelativeTime'
import { type DocumentType } from '../../../shared/domain/documentTypes'
import { generationFailedTitle } from '../../../shared/copy/documentTypeCopy'

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
        <div className={chatWorkspaceDocStyles['doc-meta']}>
          {label} · {volumePages ?? '—'} страниц · {formatRelativeTime(createdAt)}
        </div>
        {/* Server-supplied and user-influenced at once: the model writes this, answering a topic
            the user typed. It is safe only because of two react-markdown DEFAULTS — no rehype-raw
            (embedded HTML is escaped, not parsed) and the built-in urlTransform (a javascript:
            href is neutralized). Both are now pinned by DocArea.markdownSafety.test.tsx; do not
            add rehype-raw here without reading it. Tokens live in sessionStorage, so markup
            injected on this line is a session handover, not a defacement. */}
        <div
          className={`${chatWorkspaceDocStyles['doc-body']} ${docMarkdownStyles['markdown-body']}`}
          data-testid="doc-body"
        >
          <ReactMarkdown>{content ?? ''}</ReactMarkdown>
        </div>
        <div className={chatWorkspaceDocStyles['actions-row']}>
          <button
            type="button"
            className={`${chatButtonStyles['cw-btn']} ${chatWorkspaceDocStyles['cw-btn']} ${chatButtonStyles['cw-btn-primary']}`}
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
      <div className={chatWorkspaceDocStyles['doc-placeholder']} data-testid="doc-error">
        <div className={chatWorkspaceDocStyles['icon-circle']}>✕</div>
        <h2>{generationFailedTitle(documentType)}</h2>
        <p>{error ?? 'Попробуйте создать новый запрос — измените тему или требования.'}</p>
        <button
          type="button"
          className={`${chatButtonStyles['cw-btn']} ${chatWorkspaceDocStyles['cw-btn']} ${chatButtonStyles['cw-btn-primary']}`}
          data-testid="error-reset"
          onClick={onReset}
        >
          Создать новый запрос
        </button>
      </div>
    )
  }
  // `pending` и `idle` сюда больше не приходят: ожидание рисует GenerationPending, а пустой
  // экран до отправки — форма со сводкой. Обе ветки удалены вместе с двухколоночной раскладкой;
  // оставлять их значило бы держать код, который нельзя ни увидеть, ни проверить.
  return null
}
