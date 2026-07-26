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

interface ExportControlProps {
  // Null until the document has been created/loaded — there is nothing to export before then,
  // so the trigger stays disabled and no click can reach exportDocument with a missing id.
  documentId: string | null
}

export function ExportControl({ documentId }: ExportControlProps) {
  // Conditional mount, not a hidden toggle — the options are absent from the DOM
  // until the trigger is clicked, mirroring the link popover's open/close pattern.
  const [isOpen, setIsOpen] = useState(false)
  // A genuine in-flight lock, not an accident of the menu unmounting: while a request is
  // pending the options are disabled so a second click cannot dispatch a second export.
  const [isExporting, setIsExporting] = useState(false)
  // Scenario 3.2: a rejected export surfaces inline as this message (the transport's own
  // failure text) plus a retry. Null = no failure to show.
  const [error, setError] = useState<string | null>(null)
  // The format of the last dispatched attempt, captured so retry re-dispatches the SAME
  // format — a docx failure must retry docx, not a hardcoded pdf.
  const [lastFormat, setLastFormat] = useState<ExportFormat | null>(null)

  const handleExport = (format: ExportFormat) => {
    if (isExporting || !documentId) return
    setIsExporting(true)
    // Remember the format so retry re-dispatches the SAME one (docx retries docx, not pdf).
    setLastFormat(format)
    exportDocument(documentId, format)
      // Clear the error ONLY on success — never optimistically at dispatch time. This keeps a
      // failed export's banner visible through the retry's whole in-flight window and drops it
      // the moment the retry succeeds; a still-failing retry leaves the banner up.
      .then(() => {
        setError(null)
      })
      // Surface the rejection as inline error state (keeps the rejection handled — no unhandled
      // promise rejection). If the retry also rejects, the message is re-raised here.
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err))
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
        <span className="me-export-error" role="alert" data-testid="export-error">
          {error}
          <button
            type="button"
            className="me-export-retry"
            data-testid="export-retry"
            aria-label="Повторить"
            onClick={handleRetry}
          >
            Повторить
          </button>
        </span>
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
