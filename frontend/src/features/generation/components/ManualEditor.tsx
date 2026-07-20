import { useRef, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Document from '@tiptap/extension-document'
import { BlockquoteMark } from './blockquoteMark'
import { HorizontalRuleNode } from './horizontalRuleNode'
import { CodeBlockMark } from './codeBlockMark'
import { Heading3Mark } from './heading3Mark'
import { AlignCenterMark } from './alignCenterMark'
import { HardBreakKeymap } from './hardBreakKeymap'
import { HardBreakNode } from './hardBreakNode'
import './ManualEditor.css'
import type { DocumentType } from '../../../shared/documentTypes'
import { useDocumentInit } from '../hooks/useDocumentInit'
import { useDocumentSave } from '../hooks/useDocumentSave'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import { AppHeader } from '../../../shared/components/AppHeader'
import { flushDomObserverOnInput, syncNativeSelectionToProseMirror } from './editorDomSync'
import { ManualEditorToolbar } from './ManualEditorToolbar'
import { ManualEditorBreadcrumb } from './ManualEditorBreadcrumb'

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
      // hardBreak is disabled here only so HardBreakNode (below) can replace it
      // with a parse-rule override: line breaks ARE enabled for this editor
      // (scenario 3.3, approach A′), just via the dedicated node that also drops
      // ProseMirror's stray trailing-break cursor helper. See hardBreakNode.ts.
      StarterKit.configure({
        document: false,
        hardBreak: false,
        blockquote: false,
        horizontalRule: false,
        codeBlock: false,
        // Link is already registered by StarterKit — configured, not
        // re-registered. openOnClick: false is the sole barrier between an
        // anchor click and total content loss (no beforeunload guard exists on
        // this page). autolink/linkOnPaste off: both fire outside any explicit
        // user intent — autolink runs on any docChanged and setContent does not
        // set its preventAutolink meta, so a server-returned bare host would
        // silently gain an href nobody typed and the next save would persist it.
        link: { openOnClick: false, autolink: false, linkOnPaste: false },
      }),
      Document.extend({ content: 'inline*' }),
      BlockquoteMark,
      HorizontalRuleNode,
      CodeBlockMark,
      Heading3Mark,
      AlignCenterMark,
      HardBreakNode,
      HardBreakKeymap,
      Placeholder.configure({ placeholder: 'Начните печатать…' }),
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
      },
      handleDOMEvents: {
        input: (view, event) => flushDomObserverOnInput(view, event),
        select: syncNativeSelectionToProseMirror,
      },
    },
  })

  const { isSaving, saveError, setVersion, noteEdit, save } = useDocumentSave({
    documentId,
    editor,
    onSaved: () => setHasUnsavedChanges(false),
    onDirty: () => setHasUnsavedChanges(true),
  })
  noteEditRef.current = noteEdit

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
            hasFailedToInitialize={Boolean(initError)}
            onSave={save}
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
