import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import './ManualEditorSaveStatus.css'

interface ManualEditorSaveStatusProps {
  documentId: string | null
  hasUnsavedChanges: boolean
  // True once init has failed. Without it, "Создание документа…" is indistinguishable from a
  // creation that gave up a minute ago and will never finish — a progress message sitting next
  // to a Save button that cannot work, which is the most reassuring possible way to say "broken".
  hasFailedToInitialize?: boolean
}

export function ManualEditorSaveStatus({
  documentId,
  hasUnsavedChanges,
  hasFailedToInitialize = false,
}: ManualEditorSaveStatusProps) {
  if (!documentId) {
    if (hasFailedToInitialize) {
      // <output> rather than a span with role="status": it has the role implicitly, and this
      // line replaces "Создание документа…" in place, so it must be announced when it swaps in.
      return <output className="me-save-status me-save-status--failed">Документ не создан</output>
    }
    return <span className="me-save-status">Создание документа…</span>
  }

  if (hasUnsavedChanges) {
    return <span className="me-save-status me-save-status--dirty">Черновик, ещё не сохранён</span>
  }

  return (
    <span className="me-save-status me-save-status--saved">
      <PlaceholderImage />
      Сохранено
    </span>
  )
}
