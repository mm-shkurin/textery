import { useState } from 'react'
import './ExportControl.css'

// Scenario 1.1: the control DISPLAY only — a trigger that reveals a PDF and a DOCX
// choice. No API call, no download wiring yet (that is red-frontend-api). The two
// labels must read exactly "PDF" and "DOCX" because the export endpoint accepts
// format=pdf|docx and the acceptance statements assert the exact labels.
export function ExportControl() {
  // Conditional mount, not a hidden toggle — the options are absent from the DOM
  // until the trigger is clicked, mirroring the link popover's open/close pattern.
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="me-export-control">
      <button
        type="button"
        className="me-export-trigger"
        data-testid="export-control-trigger"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        Экспорт
      </button>
      {isOpen && (
        <div className="me-export-menu" role="menu" data-testid="export-menu">
          <button
            type="button"
            className="me-export-option"
            role="menuitem"
            data-testid="export-option-pdf"
          >
            PDF
          </button>
          <button
            type="button"
            className="me-export-option"
            role="menuitem"
            data-testid="export-option-docx"
          >
            DOCX
          </button>
        </div>
      )}
    </div>
  )
}
