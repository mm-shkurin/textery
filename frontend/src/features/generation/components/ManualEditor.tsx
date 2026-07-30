import { useRef, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import { BlockPlaceholder } from './blockPlaceholder'
import './ManualEditor.css'
import type { DocumentType } from '../../../shared/documentTypes'
import { useDocumentInit } from '../hooks/useDocumentInit'
import { useDocumentSave } from '../hooks/useDocumentSave'
import { useAutosave } from '../hooks/useAutosave'
import { useBeforeUnloadGuard } from '../hooks/useBeforeUnloadGuard'
import { AppHeader } from '../../../shared/components/AppHeader'
import { flushDomObserverOnInput, syncNativeSelectionToProseMirror } from './editorDomSync'
import { ManualEditorToolbar } from './ManualEditorToolbar'
import { ManualEditorBreadcrumb } from './ManualEditorBreadcrumb'
import { ManualEditorErrorBanner } from './ManualEditorErrorBanner'

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

  const editor = useEditor({
    // Tiptap v3 does not re-render on every editor transaction by default;
    // opt in so toolbar state (e.g. the bold button's aria-pressed) stays
    // in sync with the editor's current selection/marks.
    shouldRerenderOnTransaction: true,
    extensions: [
      // Full StarterKit block model (block-schema migration ADR, 2026-07-26):
      // Document is `block+`; paragraph/heading(1–3)/lists/blockquote/codeBlock/
      // horizontalRule/hardBreak are the StarterKit standard nodes, replacing the
      // bespoke inline-schema marks and the hand-rolled line-break machinery.
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        // Link is already registered by StarterKit — configured, not
        // re-registered. openOnClick: false is the sole barrier between an
        // anchor click and total content loss (no beforeunload guard exists on
        // this page). autolink/linkOnPaste off: both fire outside any explicit
        // user intent — autolink runs on any docChanged and setContent does not
        // set its preventAutolink meta, so a server-returned bare host would
        // silently gain an href nobody typed and the next save would persist it.
        link: { openOnClick: false, autolink: false, linkOnPaste: false },
      }),
      // Alignment is a block attribute now, not a wrapping <div> mark: it renders
      // as `style="text-align: …"` on the heading/paragraph it applies to.
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      BlockPlaceholder,
    ],
    content: '',
    // Every change to the document, however it was made — not just typing. The dirty flag used to
    // hang off the DOM `input` event, which a keystroke fires and a toolbar button does not:
    // bold/H3/link dispatch programmatic ProseMirror transactions straight to the state. So
    // formatting a paragraph after a save left the status reading "Сохранено" over unsent
    // markup, and the user closed a tab believing their work was persisted. `onUpdate` is the
    // one hook that sees both paths.
    //
    // `setContent` from our own save handler does NOT reach here: Tiptap treats a programmatic
    // setContent as emitUpdate: false by default, so adopting the server's sanitized HTML does
    // not re-dirty the document it just cleaned.
    onUpdate: () => noteEditRef.current(),
    editorProps: {
      attributes: {
        'data-testid': 'editor-content-area',
        // A contenteditable editing surface is a textbox in both empty and full
        // states, so role is unconditional here (NOT gated on emptiness like the
        // placeholder attrs in blockPlaceholder.ts). Without an explicit textbox
        // role, the aria-placeholder that extension emits carries no meaning to
        // assistive tech — aria-placeholder is announced only on a textbox-ish role.
        role: 'textbox',
        // Enter splits into a new block and Shift+Enter inserts a hardBreak, so
        // this textbox is multi-line. A role="textbox" defaults to single-line per
        // WAI-ARIA, so assistive tech would announce it wrong without this.
        // Unconditional like role — a textbox stays multi-line whether empty or
        // full, so it must NOT route through the emptiness-gated placeholder path.
        'aria-multiline': 'true',
      },
      handleDOMEvents: {
        input: flushDomObserverOnInput,
        select: syncNativeSelectionToProseMirror,
      },
    },
  })

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
        <ManualEditorBreadcrumb documentTypeLabel={documentTypeLabel} onBack={onBack} />
        <div className="me-editor-shell">
          <ManualEditorToolbar
            editor={editor}
            documentId={documentId}
            hasUnsavedChanges={hasUnsavedChanges}
            isSaving={isSaving}
            isRetryPending={isRetryPending}
            hasFailedToInitialize={Boolean(initError)}
            onSave={save}
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
