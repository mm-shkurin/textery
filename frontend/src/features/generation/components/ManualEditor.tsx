import { useEffect, useRef, useState } from 'react'
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
import { ManualEditorToolbar } from './ManualEditorToolbar'

export const SAVE_ERROR_MESSAGE =
  'Не удалось сохранить документ. Проверьте соединение и попробуйте ещё раз — введённый текст сохранён локально в редакторе.'

interface ManualEditorProps {
  documentType: DocumentType
  documentTypeLabel: string
  onBack: () => void
}

export function ManualEditor({ documentType, documentTypeLabel, onBack }: ManualEditorProps) {
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [version, setVersion] = useState(1)
  const [isSaving, setIsSaving] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(true)
  const [saveError, setSaveError] = useState<string | null>(null)
  const isSavingRef = useRef(false)
  const saveAgainRequested = useRef(false)

  const handleSave = () => {
    if (!documentId || !editor) return
    if (isSavingRef.current) {
      saveAgainRequested.current = true
      return
    }
    performSave(version)
  }

  const performSave = (saveVersion: number) => {
    if (!documentId || !editor) return
    isSavingRef.current = true
    setIsSaving(true)
    saveAgainRequested.current = false
    saveDocument(documentId, editor.getHTML(), saveVersion)
      .then((result) => {
        setVersion(result.version)
        setSaveError(null)
        if (saveAgainRequested.current) {
          saveAgainRequested.current = false
          performSave(result.version)
        } else {
          isSavingRef.current = false
          setIsSaving(false)
          setHasUnsavedChanges(false)
        }
      })
      .catch((error) => {
        // logging keeps the failure from being silently swallowed.
        console.error('Failed to save document', error)
        // Don't auto-retry a queued edit after a real error (out of scope: that's
        // autosave-retry behavior). Drop the queued flag so a stale retry doesn't
        // fire later, but keep the user's latest content in the editor untouched
        // so they can manually retry by clicking Save again.
        saveAgainRequested.current = false
        isSavingRef.current = false
        setIsSaving(false)
        setSaveError(SAVE_ERROR_MESSAGE)
      })
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
        input: (view, event) => {
          setHasUnsavedChanges(true)
          // An edit that lands while a save is already in flight must queue a
          // re-save even without an explicit second click on "Сохранить" —
          // otherwise the in-flight save's resolve handler has no signal that
          // newer, unsent content exists and would wrongly mark the document
          // clean (see premortem/agent-review CONCERNS on scenario 5.1's
          // green-frontend commit).
          if (isSavingRef.current) {
            saveAgainRequested.current = true
          }
          return flushDomObserverOnInput(view, event)
        },
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
          <ManualEditorToolbar
            editor={editor}
            documentId={documentId}
            hasUnsavedChanges={hasUnsavedChanges}
            isSaving={isSaving}
            onSave={handleSave}
          />
          {saveError && (
            <div className="me-error-banner" role="alert">
              <PlaceholderImage className="me-error-banner-icon" />
              {saveError}
            </div>
          )}
          <div className="me-content-area">
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </div>
  )
}
