import { useRef, useState } from 'react'
import { EditorContent } from '@tiptap/react'
import styles from './ManualEditor.module.css'
import type { DocumentType } from '../../../shared/domain/documentTypes'
import { useDocumentInit } from '../hooks/useDocumentInit'
import { useDocumentSave } from '../hooks/useDocumentSave'
import { useGeneratedDocumentInit } from '../hooks/useGeneratedDocumentInit'
import { useAutosave } from '../hooks/useAutosave'
import { useBeforeUnloadGuard } from '../hooks/useBeforeUnloadGuard'
import { AppHeader } from '../../../shared/components/AppHeader'
import { useManualEditorInstance } from '../hooks/useManualEditorInstance'
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
  // The id of the generation this editor was opened on, when the auto-transition opened it (story
  // 18, scenario 2.1) rather than history or manual mode.
  //
  // The id, NOT the generated text. The text cannot be put in the editor directly: it is the
  // model's markdown, which Tiptap renders as literal `##` characters, and it belongs to no
  // document yet so nothing can save it. Converting the generation is what produces both the HTML
  // and the document to hold it, and the conversion takes the id.
  //
  // Its presence is the one discriminator for the whole auto path: it suppresses the
  // create-a-blank-document init and drops the "Ручной режим" breadcrumb chip, because both are
  // statements about a mode this user was never asked to choose.
  generationId?: string
}

export function ManualEditor({
  documentType,
  documentTypeLabel,
  onBack,
  existingDocumentId,
  generationId,
}: ManualEditorProps) {
  const fromGeneration = generationId !== undefined
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

  const { hasPendingEditRef, isSaving, isRetryPending, saveError, setVersion, noteEdit, save } =
    useDocumentSave({
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

  // The auto path's init: seeds the generated text, converts it into a real Document, and adopts
  // the server's HTML. Mutually exclusive with useDocumentInit below, which returns early when
  // `fromGeneration` is set.
  useGeneratedDocumentInit({
    generationId,
    editor,
    setDocumentId,
    setVersion,
    onReady: () => setHasUnsavedChanges(false),
    onError: setInitError,
  })

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
    <div className={styles['manual-editor-page']} data-testid="manual-editor">
      <AppHeader />
      <div className={styles['me-container']}>
        <div className={styles['me-toolbar-row']}>
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
        <div className={styles['me-editor-shell']}>
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
          <div className={styles['me-content-area']}>
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </div>
  )
}
