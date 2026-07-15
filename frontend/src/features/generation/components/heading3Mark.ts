import { Mark, mergeAttributes } from '@tiptap/core'

// Same doc-schema mismatch as BlockquoteMark (see that file's comment): the
// document here holds inline content directly, so the built-in Heading node
// (a block node) isn't reachable. <h3>...</h3> wraps a single line the same
// shape as <blockquote>...</blockquote>, so it is modeled as a mark too.
export const Heading3Mark = Mark.create({
  name: 'heading3',
  parseHTML() {
    return [{ tag: 'h3' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['h3', mergeAttributes(HTMLAttributes), 0]
  },
})
