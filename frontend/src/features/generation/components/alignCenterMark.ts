import { Mark } from '@tiptap/core'

// Same doc-schema constraint as blockquote/heading3 (see lineWrapMark.ts): a
// Mark wraps the line instead of introducing a block node.
//
// Unlike lineWrapMark's factory (bare tag match), text-align marks all share
// the same `div` tag across center/left/right/justify - a bare tag match
// would misidentify any of them as this one. parseHTML here discriminates by
// tag AND the specific style value, so left/right/justify can each be added
// later as their own Mark sharing the div tag without collision.
export const AlignCenterMark = Mark.create({
  name: 'alignCenter',
  parseHTML() {
    return [
      {
        tag: 'div',
        getAttrs: (dom) => ((dom as HTMLElement).style.textAlign === 'center' ? {} : false),
      },
    ]
  },
  renderHTML() {
    // Not a plain ['div', attrs, 0] spec: ProseMirror's DOMSerializer applies
    // a 'style' attrs entry via `dom.style.cssText = value`, which the
    // browser/jsdom re-serializes with a trailing semicolon
    // (`text-align: center;`). Building the element directly and setting the
    // attribute via `setAttribute` keeps the exact string, matching the
    // rendered markup this mark is meant to produce.
    const dom = document.createElement('div')
    dom.setAttribute('style', 'text-align: center')
    return { dom, contentDOM: dom }
  },
})
