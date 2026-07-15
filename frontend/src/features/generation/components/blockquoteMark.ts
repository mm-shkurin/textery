import { Mark, mergeAttributes } from '@tiptap/core'

// The document schema here holds inline content directly (no paragraph
// wrapper - see the Document override in ManualEditor.tsx), so the
// built-in Blockquote extension (a block *node* requiring block+
// children) isn't reachable from this doc, and reconfiguring it as an
// inline node confuses ProseMirror's DOM-diffing (a stray empty
// <blockquote> node was observed being inserted on every keystroke, even
// with the button never clicked - see scenario 7.2 in
// 07_UI_Tests.md). A mark, exactly like the existing Bold/Strike marks,
// sidesteps the doc-schema mismatch entirely: it wraps the selected
// inline text in a <blockquote> tag without introducing a new node.
export const BlockquoteMark = Mark.create({
  name: 'blockquote',
  parseHTML() {
    return [{ tag: 'blockquote' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['blockquote', mergeAttributes(HTMLAttributes), 0]
  },
})
