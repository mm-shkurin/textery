import ReactMarkdown from 'react-markdown'
import chatButtonStyles from './ChatButton.module.css'
import chatWorkspaceDocStyles from './ChatWorkspaceDoc.module.css'
import docMarkdownStyles from './DocMarkdown.module.css'
import type { GenerationUiState } from '../hooks/useGeneration'
import { formatRelativeTime } from '../utils/formatRelativeTime'
import { type DocumentType } from '../../../shared/documentTypes'
import {
  generatingTitle,
  generationFailedTitle,
  topicPromptTitle,
} from '../../../shared/copy/documentTypeCopy'

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
  if (state === 'pending') {
    // Story 18 contract: the generating surface is marked with this testid (also scenario 1.2's
    // subject). It is present only while a generation is in flight, so a Selenium wait on it
    // observes exactly the generating state and nothing else.
    return (
      <div
        className={chatWorkspaceDocStyles['doc-placeholder']}
        data-testid="generation-generating"
      >
        <div className={chatWorkspaceDocStyles.spinner} />
        <h2>{generatingTitle(documentType)}</h2>
        <p>Обычно занимает 1–2 минуты — страница обновится автоматически</p>
      </div>
    )
  }
  return (
    <div className={chatWorkspaceDocStyles['doc-placeholder']}>
      <h2>{topicPromptTitle(documentType)}</h2>
      <p>Введите тему в панели слева — ИИ сгенерирует готовый текст.</p>
    </div>
  )
}
