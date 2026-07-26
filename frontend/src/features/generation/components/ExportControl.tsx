import { useState } from 'react'
import './ExportControl.css'

// Scenario 1.1: the control DISPLAY only — a trigger that reveals a PDF and a DOCX
// choice. No API call, no download wiring yet (that is red-frontend-api). The two
// labels must read exactly "PDF" and "DOCX" because the export endpoint accepts
// format=pdf|docx and the acceptance statements assert the exact labels — hence the
// list is keyed by the raw format value, with the label its upper-case form and the
// test id derived as export-option-<format>.
const EXPORT_FORMATS = ['pdf', 'docx'] as const

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
          {EXPORT_FORMATS.map((format) => (
            <button
              key={format}
              type="button"
              className="me-export-option"
              role="menuitem"
              data-testid={`export-option-${format}`}
            >
              {format.toUpperCase()}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
