import { useRef, useState } from 'react'
import { EditorContent } from '@tiptap/react'
import './ManualEditor.css'
import type { DocumentType } from '../../../shared/documentTypes'
import { useDocumentInit } from '../hooks/useDocumentInit'
import { useDocumentSave } from '../hooks/useDocumentSave'
import { useSeedGeneratedContent } from '../hooks/useSeedGeneratedContent'
import { useAutosave } from '../hooks/useAutosave'
import { useBeforeUnloadGuard } from '../hooks/useBeforeUnloadGuard'
import { AppHeader } from '../../../shared/components/AppHeader'
import { useManualEditorInstance } from './useManualEditorInstance'
import { ManualEditorToolbar } from './ManualEditorToolbar'
import { ManualEditorBreadcrumb } from './ManualEditorBreadcrumb'
import { ExportControl } from './ExportControl'
import { ManualEditorErrorBanner } from './ManualEditorErrorBanner'

// Re-exported: this was the message's home before the save machinery moved to useDocumentSave,
// and tests and callers import it from here.
export { SAVE_ERROR_MESSAGE } from '../hooks/useDocumentSave'

interface ManualEditorProps {
  documentType: DocumentType
  documentTypeLabel: string
  onBack: () => void
  existingDocumentId?: string
  // The text of a COMPLETED GENERATION, when the editor was opened by the auto-transition
  // (story 18, scenario 2.1) rather than from history or manual mode.
  //
  // Passed in rather than re-fetched: the flow is already holding this string — `useGeneration`
  // read it out of the poll that observed completion — so asking the server for it again would
  // be a re-read of something in hand (which scenario 2.3 exists to forbid) and would open the
  // editor EMPTY for as long as that round trip takes, on top of text the user just watched
  // being written.
  //
  // Its presence is the one discriminator for the whole auto path: it suppresses the
  // create-a-blank-document init and drops the "Ручной режим" breadcrumb chip, because both are
  // statements about a mode this user was never asked to choose.
  generatedContent?: string
}

export function ManualEditor({
  documentType,
  documentTypeLabel,
  onBack,
  existingDocumentId,
  generatedContent,
}: ManualEditorProps) {
  const fromGeneration = generatedContent !== undefined
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

  const {
    hasPendingEditRef,
    isSaving,
    isRetryPending,
    saveError,
    setVersion,
    noteEdit,
    save,
  } = useDocumentSave({
    documentId,
    editor,
    onSaved: () => setHasUnsavedChanges(false),
    onDirty: () => setHasUnsavedChanges(true),
  })
  // Every edit both marks the document dirty / queues a mid-flight re-save (noteEdit) AND resets
  // the autosave debounce so a save fires once typing stops — no explicit Сохранить click needed.
  // The manual button still calls `save` directly and is unaffected.
  const scheduleAutosave = useAutosave(save, hasPendingEditRef)
  noteEditRef.current = () => {
    noteEdit()
    scheduleAutosave()
  }

  useBeforeUnloadGuard(hasUnsavedChanges)

  useSeedGeneratedContent(editor, generatedContent)

  useDocumentInit({
    documentType,
    existingDocumentId,
    fromGeneration,
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
          <ManualEditorBreadcrumb
            documentTypeLabel={documentTypeLabel}
            onBack={onBack}
            showManualModeChip={!fromGeneration}
          />
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
            isRetryPending={isRetryPending}
            hasFailedToInitialize={Boolean(initError)}
            // save() REJECTS on failure so ExportControl can skip a stale export; the button has
            // nothing to await it, so swallow the rejection (the banner was set before the rethrow).
            onSave={() => void save().catch(() => {})}
          />
          {initError && <ManualEditorErrorBanner testId="me-init-error" message={initError} />}
          {saveError && <ManualEditorErrorBanner testId="me-save-error" message={saveError} />}
          <div className="me-content-area">
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </div>
  )
}
