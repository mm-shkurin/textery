import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'

// Tiptap's stock @tiptap/extension-placeholder decorates empty BLOCK nodes: it
// hangs `is-editor-empty` + `data-placeholder` off an empty paragraph/heading via
// Decoration.node. This editor's Document holds `inline*` content directly (no
// paragraph wrapper — see the Document override in ManualEditor.tsx), so there is
// no block node to decorate and the stock extension silently no-ops. The empty
// editor rendered a bare <br class="ProseMirror-trailingBreak"> with no attribute
// and no class, so nothing ever painted the placeholder (scenario 2.1 bug).
//
// This replaces it with a root-level decoration. ProseMirror's `attributes`
// editor prop may be a function of state (prosemirror-view computeDocDeco), and
// the values it returns are merged onto the contenteditable root element (the
// `data-testid="editor-content-area"` div) — `class` is space-joined with the
// others, other attrs are added. So while the doc is empty we return
// `is-editor-empty` + the placeholder text; ProseMirror recomputes these on every
// state update, so they reappear if the user deletes back to empty and are absent
// the moment any real content exists.
//
// Emptiness is read from `state.doc.content.size`, NOT a one-shot DOM-input flag:
// the `inline*` doc is truly empty (size 0) only when it holds no nodes. The
// <br class="ProseMirror-trailingBreak"> is a ProseMirror cursor helper in the DOM,
// never a document node (HardBreakNode ignores it on reparse — see hardBreakNode.ts),
// so it never inflates content.size. A reopened non-empty document has size > 0 and
// therefore never shows the placeholder.
export const INLINE_PLACEHOLDER_TEXT = 'Начните печатать…'

const inlinePlaceholderKey = new PluginKey('inlinePlaceholder')

export const InlinePlaceholder = Extension.create({
  name: 'inlinePlaceholder',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: inlinePlaceholderKey,
        props: {
          attributes: (state): Record<string, string> => {
            if (state.doc.content.size > 0) return {}
            return {
              class: 'is-editor-empty',
              'data-placeholder': INLINE_PLACEHOLDER_TEXT,
              // aria-placeholder carries the accessible hint data-placeholder lacks:
              // the latter is painted only via CSS ::before, which screen readers
              // announce inconsistently. Tracks emptiness exactly like the pair above
              // (dropped by the size > 0 branch), so an SR user meets a labelled,
              // textbox-role (see editorProps.attributes in ManualEditor.tsx) editor
              // while empty and loses the hint the moment real content exists.
              'aria-placeholder': INLINE_PLACEHOLDER_TEXT,
            }
          },
        },
      }),
    ]
  },
})
