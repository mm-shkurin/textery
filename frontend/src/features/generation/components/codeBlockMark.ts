import { Mark, mergeAttributes } from '@tiptap/core'

// Same doc-schema constraint as blockquote (scenario 7.2) and horizontalRule
// (scenario 7.3): the doc holds inline content directly ('inline*'), so the
// built-in CodeBlock extension (a block node) isn't reachable here. A Mark
// sidesteps that by wrapping the selected/line text instead of introducing a
// new block node.
//
// Unlike blockquote's single-tag <blockquote> wrap, the expected markup here
// is the nested <pre><code>...</code></pre> pair (verified empirically
// against the real Tiptap/ProseMirror renderHTML pipeline: a Mark's
// DOMOutputSpec supports nesting via ['pre', attrs, ['code', 0]], where the
// innermost array's `0` is the content hole - mergeAttributes({}) with no
// extra HTMLAttributes renders as no attributes on either tag, producing
// exactly '<pre><code>hello world</code></pre>').
export const CodeBlockMark = Mark.create({
  name: 'codeBlock',
  parseHTML() {
    return [
      {
        tag: 'code',
        priority: 60,
        getAttrs: (dom) => ((dom as HTMLElement).parentElement?.tagName === 'PRE' ? {} : false),
      },
    ]
  },
  renderHTML({ HTMLAttributes }) {
    return ['pre', mergeAttributes(HTMLAttributes), ['code', 0]]
  },
})
