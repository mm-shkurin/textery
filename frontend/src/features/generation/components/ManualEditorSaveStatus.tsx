import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import './ManualEditorSaveStatus.css'

interface ManualEditorSaveStatusProps {
  documentId: string | null
  hasUnsavedChanges: boolean
}

export function ManualEditorSaveStatus({ documentId, hasUnsavedChanges }: ManualEditorSaveStatusProps) {
  if (!documentId) {
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
