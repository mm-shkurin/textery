import { Node, mergeAttributes } from '@tiptap/core'

// The document schema here holds inline content directly (no paragraph
// wrapper - see the Document override in ManualEditor.tsx), so the
// built-in HorizontalRule extension (a block *node*) isn't reachable from
// this doc, same class of conflict as scenario 7.2's Blockquote. Unlike
// blockquote, <hr> is a void leaf element rather than a wrapper around
// text, so a Mark doesn't fit - a Mark needs content to wrap and <hr> has
// none. Instead this defines HorizontalRule as an inline *node* (group:
// 'inline', inline: true, atom: true), which the 'inline*' content
// schema accepts directly, exactly like an emoji/mention leaf node.
//
// Ghost-filler pitfall: registering ANY atom node with no ProseMirror-level
// required attrs into the 'inline' group makes it eligible as this
// schema's `ContentMatch.defaultType` - the node type ProseMirror falls
// back to when it needs to pad/fill content it couldn't otherwise account
// for. That fallback does fire here in practice: reconciling the
// contenteditable DOM (via view.domObserver.flush(), forced synchronously
// on every input - see editorDomSync.ts) the first time the doc goes from
// empty to non-empty silently appended an extra `horizontalRule` node with
// blank attrs, alongside the typed text, with no toolbar click involved
// (reproduced via a throwaway debug test: typing "hello world" alone into
// an empty editor produced a trailing filler node). `isRequired: true`
// (Tiptap-specific, distinct from just omitting `default`) is the one
// attribute option that stops Tiptap from injecting a schema-level
// `default` for the attribute at all, which makes
// `NodeType.hasRequiredAttrs()` true and disqualifies this node from
// `defaultType` selection - the filler never gets created. Real inserts
// (toolbar click) always supply the attribute explicitly, so they're
// unaffected.
export const HorizontalRuleNode = Node.create({
  name: 'horizontalRule',
  group: 'inline',
  inline: true,
  atom: true,
  addAttributes() {
    return {
      marker: {
        isRequired: true,
        parseHTML: () => 'hr',
        renderHTML: () => ({}),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'hr' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['hr', mergeAttributes(HTMLAttributes)]
  },
})
