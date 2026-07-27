import { useState } from 'react'
import { exportDocument, type ExportFormat } from '../api/documentApi'
import './ExportControl.css'

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

export function ExportControl({
  documentId,
  hasUnsavedChanges = false,
  save,
}: ExportControlProps) {
  // Conditional mount, not a hidden toggle — the options are absent from the DOM
  // until the trigger is clicked, mirroring the link popover's open/close pattern.
  const [isOpen, setIsOpen] = useState(false)
  // A genuine in-flight lock, not an accident of the menu unmounting: while a request is
  // pending the options are disabled so a second click cannot dispatch a second export.
  const [isExporting, setIsExporting] = useState(false)
  // Scenario 3.2: a rejected export surfaces inline as the fixed EXPORT_ERROR_MESSAGE (never the
  // caught error's own text) plus a retry. Null = no failure to show.
  const [error, setError] = useState<string | null>(null)
  // The format of the last dispatched attempt, captured so retry re-dispatches the SAME
  // format — a docx failure must retry docx, not a hardcoded pdf.
  const [lastFormat, setLastFormat] = useState<ExportFormat | null>(null)

  const handleExport = (format: ExportFormat) => {
    if (isExporting || !documentId) return
    // Set the in-flight lock BEFORE any save — the save happens inside this window so a
    // double-click during it cannot slip past the guard and double-dispatch.
    setIsExporting(true)
    // Remember the format so retry re-dispatches the SAME one (docx retries docx, not pdf).
    setLastFormat(format)
    // Scenario 4.1: on a dirty editor, persist first and dispatch only after save resolves so the
    // export never ships stale stored html. `await save()` before the export; if save REJECTS the
    // export is skipped (a failed save must not ship a stale file) and the failure surfaces as the
    // fixed banner. A clean editor skips the save entirely and exports straight through.
    const run = async () => {
      if (hasUnsavedChanges && save) {
        // Await ONLY a promise-returning save so the export waits for persistence to settle
        // (Scenario 4.1's pinned ordering). A fire-and-forget save that returns void is kicked
        // off and not awaited — awaiting `undefined` would add nothing and would needlessly defer
        // the dispatch a microtask, so we keep the synchronous path for void saves.
        const saving = save()
        if (saving && typeof saving.then === 'function') {
          await saving
        }
      }
      await exportDocument(documentId, format)
      // Clear the error ONLY on success — never optimistically at dispatch time. This keeps a
      // failed export's banner visible through the retry's whole in-flight window and drops it
      // the moment the retry succeeds; a still-failing retry leaves the banner up.
      setError(null)
    }
    run()
      // Surface any rejection (failed save OR failed export) as inline error state, keeping the
      // rejection handled — no unhandled promise rejection. If the retry also rejects, re-raised.
      .catch(() => {
        setError(EXPORT_ERROR_MESSAGE)
      })
      // `finally` releases the lock on BOTH resolve and reject: a lock that only cleared on
      // success would leave the control permanently dead after the first failed export.
      .finally(() => {
        setIsExporting(false)
      })
  }

  const handleRetry = () => {
    if (lastFormat) handleExport(lastFormat)
  }

  return (
    <div className="me-export-control">
      <button
        type="button"
        className="me-export-trigger"
        data-testid="export-control-trigger"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        disabled={!documentId}
        onClick={() => setIsOpen((open) => !open)}
      >
        Экспорт
      </button>
      {isExporting && (
        <span
          data-testid="export-spinner"
          className="me-export-spinner"
          aria-hidden="true"
        />
      )}
      {error && (
        <div className="me-export-error-bar">
          <span className="me-export-error" role="alert" data-testid="export-error">
            {error}
          </span>
          <button
            type="button"
            className="me-export-retry"
            data-testid="export-retry"
            aria-label="Повторить"
            onClick={handleRetry}
          >
            Повторить
          </button>
        </div>
      )}
      {isOpen && (
        <div className="me-export-menu" role="menu" data-testid="export-menu">
          {EXPORT_FORMATS.map((format) => (
            <button
              key={format}
              type="button"
              className="me-export-option"
              role="menuitem"
              data-testid={`export-option-${format}`}
              disabled={isExporting}
              aria-disabled={isExporting}
              onClick={() => handleExport(format)}
            >
              {format.toUpperCase()}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
