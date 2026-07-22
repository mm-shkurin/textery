import HardBreak from '@tiptap/extension-hard-break'

// hardBreak must be enabled so a line break has a schema node: in this inline-only
// Document (no paragraph wrapper — see the Document override in ManualEditor.tsx) it
// is the ONLY node that can represent a break (scenario 3.3, approach A′,
// line-break-in-inline-doc-decision.md). StarterKit's built-in hardBreak is disabled
// in favour of this one so we can harden it — same one-customization-per-file
// convention as horizontalRuleNode.ts / alignCenterMark.ts.
//
// The stray trailing <br> has TWO sources, both fixed here:
//
// 1. Ghost filler (the dominant one). A plain hardBreak is an inline node with no
//    required attrs, which makes it eligible as this `inline*` schema's
//    `ContentMatch.defaultType` — the node ProseMirror auto-injects when it needs to
//    pad/fill content. It fires here: reconciling the contenteditable DOM appends a
//    trailing hardBreak filler with no break ever typed. Exactly the HorizontalRuleNode
//    ghost-filler case. `isRequired: true` (no schema-level default) makes
//    `NodeType.hasRequiredAttrs()` true and disqualifies hardBreak from `defaultType`,
//    so the filler is never created. Real inserts supply `marker` explicitly (parsed
//    <br> via the attribute's parseHTML; keyboard inserts via HardBreakKeymap).
//
// 2. Cursor-helper reparse. ProseMirror renders a <br class="ProseMirror-trailingBreak">
//    cursor helper at the end of inline content; the forced synchronous
//    domObserver.flush() (editorDomSync.ts) would reparse it into a real trailing
//    hardBreak. A higher-priority parse rule IGNORES that helper element so it is never
//    read into the document. A real, user-inserted break renders as a bare <br> (no
//    ProseMirror-trailingBreak class), doesn't match this rule, and is kept by the
//    ordinary `br` rule — interior breaks survive, only the stray trailing one dies.
export const HardBreakNode = HardBreak.extend({
  addAttributes() {
    return {
      marker: {
        isRequired: true,
        parseHTML: () => 'br',
        renderHTML: () => ({}),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'br.ProseMirror-trailingBreak', ignore: true, priority: 100 }, { tag: 'br' }]
  },
})
