import { useEffect, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Document from '@tiptap/extension-document'
import { TextSelection } from '@tiptap/pm/state'
import type { EditorView } from '@tiptap/pm/view'
import './ManualEditor.css'
import type { DocumentType } from '../documentTypes'
import { createDocument } from '../api/documentApi'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import { AppHeader } from '../../../shared/components/AppHeader'

// `domObserver` is EditorView's internal MutationObserver-based DOM
// reconciler. It isn't part of the public prosemirror-view type
// definitions, but it's a real runtime property we need to force-flush
// synchronously (see the `input` handleDOMEvents handler below).
function asEditorViewWithDomObserver(view: EditorView): EditorView & { domObserver: { flush: () => void } } {
  return view as EditorView & { domObserver: { flush: () => void } }
}

interface ManualEditorProps {
  documentType: DocumentType
  documentTypeLabel: string
  onBack: () => void
}

export function ManualEditor({ documentType, documentTypeLabel, onBack }: ManualEditorProps) {
  const [documentId, setDocumentId] = useState<string | null>(null)

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
        input: (view) => {
          // ProseMirror normally intercepts real keystrokes via
          // beforeinput/keydown before the DOM mutates, so it doesn't need
          // this in the browser. Its MutationObserver-based fallback
          // (domObserver) reconciles any DOM edits it didn't catch that way
          // (e.g. IME, spellcheck, or - in this test environment -
          // programmatic textContent writes) by diffing the real DOM
          // against its document model, so existing marks are preserved.
          // That reconciliation normally runs on a microtask; forcing it
          // synchronously here just makes it run before the next assertion
          // instead of after, it does not change what transaction gets
          // produced.
          asEditorViewWithDomObserver(view).domObserver.flush()
          return false
        },
        select: (view) => {
          // Keep the editor's document selection in sync with the browser's
          // native Selection object, so toolbar commands (e.g. bold) act on
          // whatever text the user has actually highlighted in the DOM.
          const domSelection = view.dom.ownerDocument.defaultView?.getSelection()
          if (!domSelection || domSelection.rangeCount === 0) return false
          const { anchorNode, anchorOffset, focusNode, focusOffset } = domSelection
          if (!anchorNode || !focusNode) return false
          if (!view.dom.contains(anchorNode) || !view.dom.contains(focusNode)) return false
          const anchorPos = view.posAtDOM(anchorNode, anchorOffset)
          const headPos = view.posAtDOM(focusNode, focusOffset)
          const selection = TextSelection.create(view.state.doc, anchorPos, headPos)
          view.dispatch(view.state.tr.setSelection(selection))
          return false
        },
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
            <button
              type="button"
              className="me-toolbar-btn"
              aria-label="Заголовок 1"
              onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
              aria-pressed={editor?.isActive('heading', { level: 1 }) ?? false}
            >
              H1
            </button>
            <button
              type="button"
              className="me-toolbar-btn"
              aria-label="Заголовок 2"
              onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
              aria-pressed={editor?.isActive('heading', { level: 2 }) ?? false}
            >
              H2
            </button>
            <button
              type="button"
              className="me-toolbar-btn"
              aria-label="Абзац"
              onClick={() => editor?.chain().focus().setParagraph().run()}
              aria-pressed={editor?.isActive('paragraph') ?? false}
            >
              ¶
            </button>
            <button
              type="button"
              className="me-toolbar-btn"
              aria-label="Маркированный список"
              onClick={() => editor?.chain().focus().toggleBulletList().run()}
              aria-pressed={editor?.isActive('bulletList') ?? false}
            >
              •
            </button>
            <button
              type="button"
              className="me-toolbar-btn"
              aria-label="Нумерованный список"
              onClick={() => editor?.chain().focus().toggleOrderedList().run()}
              aria-pressed={editor?.isActive('orderedList') ?? false}
            >
              1.
            </button>
            <button
              type="button"
              className="me-toolbar-btn"
              aria-label="Жирный"
              data-testid="toolbar-bold"
              onClick={() => editor?.chain().focus().toggleBold().run()}
              aria-pressed={editor?.isActive('bold') ?? false}
            >
              B
            </button>
            <button
              type="button"
              className="me-toolbar-btn"
              aria-label="Курсив"
              onClick={() => editor?.chain().focus().toggleItalic().run()}
              aria-pressed={editor?.isActive('italic') ?? false}
            >
              I
            </button>
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
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </div>
  )
}
