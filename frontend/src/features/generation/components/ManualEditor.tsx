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
import './ManualEditor.css'
import type { DocumentType } from '../documentTypes'
import { saveDocument } from '../api/documentApi'
import { useDocumentInit } from '../hooks/useDocumentInit'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import { AppHeader } from '../../../shared/components/AppHeader'
import { flushDomObserverOnInput, syncNativeSelectionToProseMirror } from './editorDomSync'
import { ManualEditorToolbar } from './ManualEditorToolbar'
import { ManualEditorBreadcrumb } from './ManualEditorBreadcrumb'

export const SAVE_ERROR_MESSAGE =
  'Не удалось сохранить документ. Проверьте соединение и попробуйте ещё раз — введённый текст сохранён локально в редакторе.'

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
    // Captured before the round trip: the response's content is the SANITIZED persisted form,
    // and telling whether to adopt it requires knowing what we actually sent.
    const sent = editor.getHTML()
    saveDocument(documentId, sent, saveVersion)
      .then((result) => {
        // The server's content is the source of truth — it strips <script> with its contents and
        // normalises void tags (`<br />` -> `<br>`), measured 2026-07-17. Keeping ours would
        // render markup the server does not have and re-send it on every later save.
        //
        // But adopt ONLY if the editor still holds exactly what we sent. Typing continues while
        // the request is in flight, and setContent would delete those keystrokes — the worst
        // possible trade for cosmetic agreement. If it changed, the next save re-sanitizes
        // anyway, so nothing is lost by skipping.
        if (result.content !== sent && editor.getHTML() === sent) {
          editor.commands.setContent(result.content)
        }
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

  useDocumentInit({ documentType, existingDocumentId, editor, setDocumentId, setVersion })

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
