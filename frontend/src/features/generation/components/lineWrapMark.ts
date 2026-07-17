import { Mark, mergeAttributes } from '@tiptap/core'

// The document schema here holds inline content directly (no paragraph
// wrapper - see the Document override in ManualEditor.tsx), so block-level
// built-in extensions (Blockquote, Heading, ...) aren't reachable from this
// doc: they are block *nodes* requiring block+ children, and reconfiguring
// one as an inline node confuses ProseMirror's DOM-diffing (a stray empty
// <blockquote> node was observed being inserted on every keystroke, even
// with the button never clicked - see scenario 7.2 in 07_UI_Tests.md). A
// mark, exactly like the existing Bold/Strike marks, sidesteps the
// doc-schema mismatch entirely: it wraps the selected/line text in a single
// HTML tag without introducing a new node.
//
// This factory covers marks that wrap in exactly one tag (<blockquote>,
// <h3>, ...). codeBlockMark.ts is NOT built on this factory: it needs the
// nested <pre><code>...</code></pre> shape, which this single-tag factory
// can't express.
export function createLineWrapMark(name: string, tag: string) {
  return Mark.create({
    name,
    parseHTML() {
      return [{ tag }]
    },
    renderHTML({ HTMLAttributes }) {
      return [tag, mergeAttributes(HTMLAttributes), 0]
    },
  })
}
