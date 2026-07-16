import './ManualEditorBreadcrumb.css'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'

interface ManualEditorBreadcrumbProps {
  documentTypeLabel: string
  onBack: () => void
}

// Pure presentation: the back affordance and the "{type} · Ручной режим" chips.
// Extracted from ManualEditor alongside ManualEditorToolbar/ManualEditorSaveStatus
// so that component reads as save orchestration + editor config + layout, with
// the markup behind names. Holds no editor or save coupling.
export function ManualEditorBreadcrumb({ documentTypeLabel, onBack }: ManualEditorBreadcrumbProps) {
  return (
    <div className="me-breadcrumb">
      <button type="button" className="me-breadcrumb-back" onClick={onBack} aria-label="Назад">
        <span aria-hidden="true">←</span>
        Назад
      </button>
      <div data-testid="editor-breadcrumb" className="me-breadcrumb-chips">
        <span className="me-breadcrumb-chip">
          <span className="me-chip-icon">
            <PlaceholderImage />
          </span>
          {documentTypeLabel}
        </span>
        <span className="me-breadcrumb-sep"> · </span>
        <span className="me-breadcrumb-chip">
          <span className="me-chip-icon">
            <PlaceholderImage />
          </span>
          Ручной режим
        </span>
      </div>
    </div>
  )
}
