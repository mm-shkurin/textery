import type { MutableRefObject } from 'react'
import { useEditor, type Editor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Document from '@tiptap/extension-document'
import { BlockquoteMark } from './blockquoteMark'
import { HorizontalRuleNode } from './horizontalRuleNode'
import { CodeBlockMark } from './codeBlockMark'
import { Heading3Mark } from './heading3Mark'
import { AlignCenterMark } from './alignCenterMark'
import { HardBreakKeymap } from './hardBreakKeymap'
import { HardBreakNode } from './hardBreakNode'
import { InlinePlaceholder } from './inlinePlaceholder'
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
      InlinePlaceholder,
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
        // placeholder attrs in inlinePlaceholder.ts). Without an explicit textbox
        // role, the aria-placeholder that plugin emits carries no meaning to
        // assistive tech — aria-placeholder is announced only on a textbox-ish role.
        role: 'textbox',
        // Enter inserts a HardBreakNode (line breaks are enabled), so this textbox
        // is multi-line. A role="textbox" defaults to single-line per WAI-ARIA, so
        // assistive tech would announce it wrong without this. Unconditional like
        // role — a textbox stays multi-line whether empty or full, so it must NOT
        // route through the emptiness-gated placeholder decoration path.
        'aria-multiline': 'true',
      },
      handleDOMEvents: {
        input: (view, event) => flushDomObserverOnInput(view, event),
        select: syncNativeSelectionToProseMirror,
      },
    },
  })
}
