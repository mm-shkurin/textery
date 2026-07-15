import { Fragment, useEffect, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Document from '@tiptap/extension-document'
import './ManualEditor.css'
import type { DocumentType } from '../documentTypes'
import { createDocument, saveDocument } from '../api/documentApi'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import { AppHeader } from '../../../shared/components/AppHeader'
import { flushDomObserverOnInput, syncNativeSelectionToProseMirror } from './editorDomSync'
import { TOOLBAR_ACTIONS, TOOLBAR_DIVIDER_BEFORE } from './editorToolbarActions'

interface ManualEditorProps {
  documentType: DocumentType
  documentTypeLabel: string
  onBack: () => void
}

export function ManualEditor({ documentType, documentTypeLabel, onBack }: ManualEditorProps) {
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [version, setVersion] = useState(1)
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = () => {
    if (isSaving || !documentId || !editor) return
    setIsSaving(true)
    saveDocument(documentId, editor.getHTML(), version)
      .then((result) => setVersion(result.version))
      .finally(() => setIsSaving(false))
  }

  const editor = useEditor({
    // Tiptap v3 does not re-render on every editor transaction by default;
    // opt in so toolbar state (e.g. the bold button's aria-pressed) stays
    // in sync with the editor's current selection/marks.
    shouldRerenderOnTransaction: true,
    extensions: [
      // hardBreak is disabled: its schema node interacts badly with
      // ProseMirror's contenteditable "trailing break" cursor helper when
      // the document itself holds inline content directly (no paragraph
      // wrapper), producing a stray <br> even for non-empty content. This
      // editor doesn't need hard breaks for the current scope.
      StarterKit.configure({ document: false, hardBreak: false }),
      Document.extend({ content: 'inline*' }),
      Placeholder.configure({ placeholder: 'Начните печатать…' }),
    ],
    content: '',
    editorProps: {
      attributes: {
        'data-testid': 'editor-content-area',
      },
      handleDOMEvents: {
        input: flushDomObserverOnInput,
        select: syncNativeSelectionToProseMirror,
      },
    },
  })

  useEffect(() => {
    let cancelled = false
    createDocument(documentType)
      .then((result) => {
        if (!cancelled) setDocumentId(result.documentId)
      })
      .catch((error) => {
        // Error surfacing (retry/UI state) is out of scope for this scenario;
        // logging keeps the failure from being silently swallowed.
        console.error('Failed to create document', error)
      })
    return () => {
      cancelled = true
    }
  }, [documentType])

  return (
    <div className="manual-editor-page" data-testid="manual-editor">
      <AppHeader />
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
            {TOOLBAR_ACTIONS.map((action) => (
              <Fragment key={action.key}>
                {TOOLBAR_DIVIDER_BEFORE.has(action.key) && (
                  <div className="me-toolbar-divider" aria-hidden="true" />
                )}
                <button
                  type="button"
                  className="me-toolbar-btn"
                  aria-label={action.ariaLabel}
                  data-testid={action.testId}
                  onClick={() => editor && action.run(editor)}
                  aria-pressed={editor ? action.isActive(editor) : false}
                >
                  {action.label}
                </button>
              </Fragment>
            ))}
            <div className="me-toolbar-status">
              <span className="me-save-status">
                {documentId ? 'Черновик, ещё не сохранён' : 'Создание документа…'}
              </span>
              <button
                type="button"
                className="me-save-btn"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving && <span data-testid="save-spinner" className="me-save-spinner" aria-hidden="true" />}
                Сохранить
              </button>
            </div>
          </div>
          <div className="me-content-area">
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </div>
  )
}
