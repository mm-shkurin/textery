import { useEffect, useState } from 'react'
import './ManualEditor.css'
import type { DocumentType } from '../documentTypes'
import { createDocument } from '../api/documentApi'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'

interface ManualEditorProps {
  documentType: DocumentType
  documentTypeLabel: string
  onBack: () => void
}

const TOOLBAR_BUTTONS = [
  { label: 'H1', aria: 'Заголовок 1' },
  { label: 'H2', aria: 'Заголовок 2' },
  { label: '¶', aria: 'Абзац' },
  { label: '•', aria: 'Маркированный список' },
  { label: '1.', aria: 'Нумерованный список' },
  { label: 'B', aria: 'Жирный' },
  { label: 'I', aria: 'Курсив' },
]

export function ManualEditor({ documentType, documentTypeLabel, onBack }: ManualEditorProps) {
  const [documentId, setDocumentId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    createDocument(documentType)
      .then((result) => {
        if (!cancelled) setDocumentId(result.documentId)
      })
      .catch(() => {
        // Error surfacing for a failed create is out of scope for this scenario.
      })
    return () => {
      cancelled = true
    }
  }, [documentType])

  return (
    <div className="manual-editor-page" data-testid="manual-editor">
      <header className="me-header">
        <img className="me-logo" src="/logo.svg" alt="Textery" />
      </header>
      <div className="me-container">
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
        <div className="me-editor-shell">
          <div className="me-toolbar">
            {TOOLBAR_BUTTONS.map((btn) => (
              <button key={btn.aria} type="button" className="me-toolbar-btn" aria-label={btn.aria}>
                {btn.label}
              </button>
            ))}
            <div className="me-toolbar-status">
              <span className="me-save-status">
                {documentId ? 'Черновик, ещё не сохранён' : 'Создание документа…'}
              </span>
              <button type="button" className="me-save-btn">
                Сохранить
              </button>
            </div>
          </div>
          <div className="me-content-area">
            <div className="me-placeholder">Начните печатать…</div>
          </div>
        </div>
      </div>
    </div>
  )
}
