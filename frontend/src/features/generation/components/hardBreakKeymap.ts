import { Extension } from '@tiptap/core'

// The Document here holds `inline*` content directly (no paragraph wrapper — see
// the Document override in ManualEditor.tsx). StarterKit's default Enter keymap
// splits the enclosing block/paragraph; with no block to split, plain Enter is a
// no-op in this schema, so a user pressing Enter gets nothing (scenario 3.3 bug).
//
// hardBreak is the only schema node that can represent a line break in an
// inline-only doc, so both plain Enter and Shift-Enter are bound to insert one.
//
// It inserts with an explicit `marker` attr rather than calling `setHardBreak()`:
// HardBreakNode makes `marker` a required attr (isRequired, no default) to keep
// hardBreak out of the schema's defaultType filler slot — see hardBreakNode.ts.
// setHardBreak creates the node with no attrs, which would throw "No value supplied
// for attribute marker"; insertContent lets us supply it.
export const HardBreakKeymap = Extension.create({
  name: 'hardBreakKeymap',
  addKeyboardShortcuts() {
    const insertBreak = () =>
      this.editor.commands.insertContent({ type: 'hardBreak', attrs: { marker: 'br' } })
    return {
      Enter: insertBreak,
      'Shift-Enter': insertBreak,
    }
  },
})
