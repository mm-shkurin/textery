import styles from './ManualEditorBreadcrumb.module.css'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'

interface ManualEditorBreadcrumbProps {
  documentTypeLabel: string
  onBack: () => void
  // Whether the "Ручной режим" chip renders beside the type chip.
  //
  // CONDITIONAL, NOT DELETED, and the distinction is load-bearing. Story 18 opens this same
  // editor on two paths: the history-open path still sets mode='manual'
  // (`useFlowNavigation.openDocumentFromHistory`) and is under a live, un-skipped acceptance
  // assertion — `manual_editor_statements.EXPECTED_DOKLAD_BREADCRUMB = "Доклад · Ручной режим"`,
  // consumed by `test_manual_editor_acceptance.py`. Scenario 2.1's auto path did not choose a
  // mode at all (the mode modal was removed), so labelling it "Ручной режим" would name a choice
  // the user was never offered. Dropping the chip outright would break the manual path's suite.
  showManualModeChip: boolean
}

// Pure presentation: the back affordance and the "{type} · Ручной режим" chips.
// Extracted from ManualEditor alongside ManualEditorToolbar/ManualEditorSaveStatus
// so that component reads as save orchestration + editor config + layout, with
// the markup behind names. Holds no editor or save coupling.
export function ManualEditorBreadcrumb({
  documentTypeLabel,
  onBack,
  showManualModeChip,
}: ManualEditorBreadcrumbProps) {
  return (
    <div className={styles['me-breadcrumb']}>
      <button
        type="button"
        className={styles['me-breadcrumb-back']}
        onClick={onBack}
        aria-label="Назад"
      >
        <span aria-hidden="true">←</span>
        Назад
      </button>
      <div data-testid="editor-breadcrumb" className={styles['me-breadcrumb-chips']}>
        <span className={styles['me-breadcrumb-chip']}>
          <span className={styles['me-chip-icon']}>
            <PlaceholderImage />
          </span>
          {documentTypeLabel}
        </span>
        {showManualModeChip && (
          <>
            <span className={styles['me-breadcrumb-sep']}> · </span>
            <span className={styles['me-breadcrumb-chip']}>
              <span className={styles['me-chip-icon']}>
                <PlaceholderImage />
              </span>
              Ручной режим
            </span>
          </>
        )}
      </div>
    </div>
  )
}
