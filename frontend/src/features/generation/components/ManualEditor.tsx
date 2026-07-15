import { Fragment, useEffect, useRef, useState } from 'react'
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
import { ManualEditorSaveStatus } from './ManualEditorSaveStatus'

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
        // Error surfacing (retry/UI state) is out of scope for this scenario;
        // logging keeps the failure from being silently swallowed.
        console.error('Failed to save document', error)
        // Don't auto-retry a queued edit after a real error (out of scope: that's
        // autosave-retry behavior). Drop the queued flag so a stale retry doesn't
        // fire later, but keep the user's latest content in the editor untouched
        // so they can manually retry by clicking Save again.
        saveAgainRequested.current = false
        isSavingRef.current = false
        setIsSaving(false)
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
              <ManualEditorSaveStatus documentId={documentId} hasUnsavedChanges={hasUnsavedChanges} />
              {/*
                aria-disabled (not the native disabled attribute) so the
                button keeps receiving click/keyboard events while a save is
                in flight. A natively disabled <button> never dispatches
                click at all (not a jsdom quirk — that's spec behavior), so
                a click during isSaving would be silently lost instead of
                reaching handleSave's own in-flight guard, which is what
                queues the "save again" intent.
              */}
              <button
                type="button"
                className="me-save-btn"
                aria-disabled={isSaving}
                onClick={handleSave}
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
