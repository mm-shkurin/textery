import type { MutableRefObject } from 'react'
import { useEditor, type Editor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import TextAlign from '@tiptap/extension-text-align'
import { BlockPlaceholder } from './blockPlaceholder'
import { flushDomObserverOnInput, syncNativeSelectionToProseMirror } from './editorDomSync'

// The Tiptap editor construction for ManualEditor, extracted so the component keeps to its layout
// and wiring concerns. `noteEditRef` (not the raw noteEdit) is threaded in because useEditor's
// handleDOMEvents needs `noteEdit`, and useDocumentSave needs the `editor` that useEditor returns —
// a cycle in source order only. The ref breaks it: the input handler reads it when an edit happens,
// which is long after the assignment in the component has run.
export function useManualEditorInstance(
  noteEditRef: MutableRefObject<() => void>,
): Editor | null {
  return useEditor({
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
        // anchor click and total content loss. autolink/linkOnPaste off: both
        // fire outside any explicit user intent — autolink runs on any
        // docChanged and setContent does not set its preventAutolink meta, so a
        // server-returned bare host would silently gain an href nobody typed and
        // the next save would persist it.
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
}
