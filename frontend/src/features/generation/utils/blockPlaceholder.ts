import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import type { EditorState } from '@tiptap/pm/state'

// Root-level placeholder for the block-content editor. Stock
// @tiptap/extension-placeholder hangs `is-editor-empty` + `data-placeholder`
// off the empty BLOCK node's decoration (the empty <p>), and never emits
// aria-placeholder. This editor pins all three surfaces on the contenteditable
// ROOT element (data-testid="editor-content-area") — the Selenium tests and the
// jsdom placeholder tests read them there — and needs the accessible
// aria-placeholder hint too. So the surfaces are emitted as root attributes via
// the ProseMirror `attributes` editor prop (a function of state), recomputed on
// every state update: they appear while the document is empty and vanish the
// moment real content exists.
//
// Emptiness for a `block+` document: exactly one child, a paragraph textblock
// holding no inline content. A lone hardBreak (`<br>` → size 1) or an &nbsp;
// text node (size 1) is NOT empty. Whitespace that the parser strips collapses
// to a single empty paragraph and IS treated as empty (blank box, but labelled).
export const BLOCK_PLACEHOLDER_TEXT = 'Начните печатать…'

const blockPlaceholderKey = new PluginKey('blockPlaceholder')

function isEmptyBlockDoc(state: EditorState): boolean {
  const { doc } = state
  if (doc.childCount !== 1) return false
  const first = doc.firstChild
  return first !== null && first.isTextblock && first.content.size === 0
}

export const BlockPlaceholder = Extension.create({
  name: 'blockPlaceholder',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: blockPlaceholderKey,
        props: {
          attributes: (state): Record<string, string> => {
            if (!isEmptyBlockDoc(state)) return {}
            return {
              class: 'is-editor-empty',
              'data-placeholder': BLOCK_PLACEHOLDER_TEXT,
              'aria-placeholder': BLOCK_PLACEHOLDER_TEXT,
            }
          },
        },
      }),
    ]
  },
})
