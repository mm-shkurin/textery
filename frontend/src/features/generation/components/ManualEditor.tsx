import { useEffect, useRef, useState } from 'react'
import { EditorContent } from '@tiptap/react'
import './ManualEditor.css'
import type { DocumentType } from '../../../shared/documentTypes'
import { useDocumentInit } from '../hooks/useDocumentInit'
import { useDocumentSave } from '../hooks/useDocumentSave'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import { AppHeader } from '../../../shared/components/AppHeader'
import { useManualEditorInstance } from './useManualEditorInstance'
import { ManualEditorToolbar } from './ManualEditorToolbar'
import { ManualEditorBreadcrumb } from './ManualEditorBreadcrumb'
import { ExportControl } from './ExportControl'

// Re-exported: this was the message's home before the save machinery moved to useDocumentSave,
// and tests and callers import it from here.
export { SAVE_ERROR_MESSAGE } from '../hooks/useDocumentSave'

interface ManualEditorProps {
  documentType: DocumentType
  documentTypeLabel: string
  onBack: () => void
  existingDocumentId?: string
}

export function ManualEditor({
  documentType,
  documentTypeLabel,
  onBack,
  existingDocumentId,
}: ManualEditorProps) {
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(true)
  // Init failing is worse than a save failing and must not be quieter: with no documentId there
  // is nothing to save TO, so the button below is inert and the text the user types has nowhere
  // to go. Kept separate from `saveError` because they can both be true and they say different
  // things — one means "this attempt failed, try again", the other "this editor cannot persist".
  const [initError, setInitError] = useState<string | null>(null)

  // useEditor's handleDOMEvents needs `noteEdit`, and useDocumentSave needs the `editor` that
  // useEditor returns — a cycle in source order only. The ref breaks it: the input handler reads
  // it when an edit happens, which is long after the assignment below has run.
  const noteEditRef = useRef<() => void>(() => {})

  const editor = useManualEditorInstance(noteEditRef)

  const { isSaving, saveError, setVersion, noteEdit, save } = useDocumentSave({
    documentId,
    editor,
    onSaved: () => setHasUnsavedChanges(false),
    onDirty: () => setHasUnsavedChanges(true),
  })
  noteEditRef.current = noteEdit

  // Unsaved work lives only in Tiptap's in-memory state, so a tab-close or refresh drops it
  // silently. beforeunload's native "leave?" prompt is the browser's one built-in defence, shown
  // only when a listener calls preventDefault. Arm it while dirty, and detach on clean/unmount with
  // the same handler reference so a closed editor cannot keep blocking navigation.
  useEffect(() => {
    if (!hasUnsavedChanges) return
    const guard = (event: BeforeUnloadEvent) => {
      // preventDefault marks the event cancelled on current Chromium, but legacy Chrome/Edge and
      // older Safari/Firefox only show the native "leave?" prompt when returnValue is also set —
      // without it the guard would arm yet display nothing on a subset of supported browsers.
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', guard)
    return () => window.removeEventListener('beforeunload', guard)
  }, [hasUnsavedChanges])

  useDocumentInit({
    documentType,
    existingDocumentId,
    editor,
    setDocumentId,
    setVersion,
    onError: setInitError,
  })

  return (
    <div className="manual-editor-page" data-testid="manual-editor">
      <AppHeader />
      <div className="me-container">
        <div className="me-toolbar-row">
          <ManualEditorBreadcrumb documentTypeLabel={documentTypeLabel} onBack={onBack} />
          <ExportControl
            documentId={documentId}
            hasUnsavedChanges={hasUnsavedChanges}
            save={save}
          />
        </div>
        <div className="me-editor-shell">
          <ManualEditorToolbar
            editor={editor}
            documentId={documentId}
            hasUnsavedChanges={hasUnsavedChanges}
            isSaving={isSaving}
            hasFailedToInitialize={Boolean(initError)}
            // save() REJECTS on failure so ExportControl can skip a stale export; the button has
            // nothing to await it, so swallow the rejection (the banner was set before the rethrow).
            onSave={() => void save().catch(() => {})}
          />
          {initError && (
            <div className="me-error-banner" role="alert" data-testid="me-init-error">
              <PlaceholderImage className="me-error-banner-icon" />
              {initError}
            </div>
          )}
          {saveError && (
            <div className="me-error-banner" role="alert" data-testid="me-save-error">
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
