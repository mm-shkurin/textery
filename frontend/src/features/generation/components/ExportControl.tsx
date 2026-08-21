import { useState } from 'react'
import type { ExportFormat } from '../api/documentApi'
import styles from './ExportControl.module.css'
import { runExport } from '../utils/exportRun'

// Scenario 1.1: the control DISPLAY — a trigger that reveals a PDF and a DOCX choice.
// Scenario 2.1: clicking a choice fires the export request and the control locks while it is
// in flight, so a double-click cannot dispatch two requests. The two labels must read exactly
// "PDF" and "DOCX" because the export endpoint accepts format=pdf|docx and the acceptance
// statements assert the exact labels — the list is keyed by the raw format value, the label its
// upper-case form, and the test id derived as export-option-<format>.
const EXPORT_FORMATS: ExportFormat[] = ['pdf', 'docx']

// Scenario 3.2: every export failure surfaces this ONE localized message. We never render the
// caught error's own text — a transport-layer rejection ("Failed to fetch") or a non-Error throw
// ("boom") must not leak raw wording into the banner, so the message is fixed here, not derived.
const EXPORT_ERROR_MESSAGE = 'Не удалось экспортировать документ'

// The control's whole position, as one value: whether the menu is revealed, whether a request
// holds the lock, what failed, and which format the failure was for. They move together — a
// dispatch opens the lock AND records the format, a success clears the banner — and held apart
// they were four switches that had to be kept in step by hand.
interface ExportState {
  // Conditional mount, not a hidden toggle — the options are absent from the DOM
  // until the trigger is clicked, mirroring the link popover's open/close pattern.
  isOpen: boolean
  // A genuine in-flight lock, not an accident of the menu unmounting: while a request is
  // pending the options are disabled so a second click cannot dispatch a second export.
  isExporting: boolean
  // Scenario 3.2: a rejected export surfaces inline as the fixed EXPORT_ERROR_MESSAGE (never the
  // caught error's own text) plus a retry. Null = no failure to show.
  error: string | null
  // The format of the last dispatched attempt, captured so retry re-dispatches the SAME
  // format — a docx failure must retry docx, not a hardcoded pdf.
  lastFormat: ExportFormat | null
}

const IDLE: ExportState = { isOpen: false, isExporting: false, error: null, lastFormat: null }

interface ExportControlProps {
  // Null until the document has been created/loaded — there is nothing to export before then,
  // so the trigger stays disabled and no click can reach exportDocument with a missing id.
  documentId: string | null
  // Scenario 4.1 (SAVE-FIRST): export renders the STORED html. When the editor holds unsaved
  // edits, the file would ship stale — so we persist first and dispatch the export only after the
  // save resolves. Optional so the many call sites that never carry dirty state (and the existing
  // tests) keep working: absent/false means "already current", export straight through, no save.
  hasUnsavedChanges?: boolean
  // Reuses ManualEditor's existing save machinery (useDocumentSave). Typed to accept both the
  // real fire-and-return-void save and a promise-returning one so the export can `await` it either
  // way and only dispatch once it has settled.
  save?: () => void | Promise<void>
}

function ExportErrorBar({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className={styles['me-export-error-bar']}>
      <span className={styles['me-export-error']} role="alert" data-testid="export-error">
        {error}
      </span>
      <button
        type="button"
        className={styles['me-export-retry']}
        data-testid="export-retry"
        aria-label="Повторить"
        onClick={onRetry}
      >
        Повторить
      </button>
    </div>
  )
}

function ExportMenu({
  isExporting,
  onExport,
}: {
  isExporting: boolean
  onExport: (format: ExportFormat) => void
}) {
  return (
    <div className={styles['me-export-menu']} role="menu" data-testid="export-menu">
      {EXPORT_FORMATS.map((format) => (
        <button
          key={format}
          type="button"
          className={styles['me-export-option']}
          role="menuitem"
          data-testid={`export-option-${format}`}
          disabled={isExporting}
          aria-disabled={isExporting}
          onClick={() => onExport(format)}
        >
          {format.toUpperCase()}
        </button>
      ))}
    </div>
  )
}

export function ExportControl({ documentId, hasUnsavedChanges = false, save }: ExportControlProps) {
  const [state, setState] = useState<ExportState>(IDLE)

  const handleExport = (format: ExportFormat) => {
    if (state.isExporting || !documentId) return
    // The in-flight lock is set BEFORE any save — the save happens inside this window so a
    // double-click during it cannot slip past the guard and double-dispatch — and the format is
    // recorded with it so retry re-dispatches the SAME one (docx retries docx, not pdf).
    setState((current) => ({ ...current, isExporting: true, lastFormat: format }))
    runExport(documentId, format, hasUnsavedChanges ? save : undefined)
      // Cleared ONLY on a delivered file — never optimistically at dispatch time. This keeps a
      // failed export's banner visible through the retry's whole in-flight window and drops it
      // the moment the retry succeeds; a still-failing retry leaves the banner up. A skipped
      // export (the save failed) leaves the banner exactly as it was — ManualEditor's save-error
      // banner is the accurate one there, and this generic message would only mask it.
      .then((delivered) => {
        if (delivered) setState((current) => ({ ...current, error: null }))
      })
      // Surface an export rejection as inline error state, keeping the rejection handled — no
      // unhandled promise rejection.
      .catch(() => setState((current) => ({ ...current, error: EXPORT_ERROR_MESSAGE })))
      // `finally` releases the lock on BOTH resolve and reject: a lock that only cleared on
      // success would leave the control permanently dead after the first failed export.
      .finally(() => setState((current) => ({ ...current, isExporting: false })))
  }

  return (
    <div className={styles['me-export-control']}>
      <button
        type="button"
        className={styles['me-export-trigger']}
        data-testid="export-control-trigger"
        aria-haspopup="menu"
        aria-expanded={state.isOpen}
        disabled={!documentId}
        onClick={() => setState((current) => ({ ...current, isOpen: !current.isOpen }))}
      >
        Экспорт
      </button>
      {state.isExporting && (
        <span
          data-testid="export-spinner"
          className={styles['me-export-spinner']}
          aria-hidden="true"
        />
      )}
      {state.error && (
        <ExportErrorBar
          error={state.error}
          onRetry={() => {
            if (state.lastFormat) handleExport(state.lastFormat)
          }}
        />
      )}
      {state.isOpen && <ExportMenu isExporting={state.isExporting} onExport={handleExport} />}
    </div>
  )
}
