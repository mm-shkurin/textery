# Decision: Line break (Enter) in the inline* editor document

**Date**: 2026-07-20 **Scenarios**: manual-mode line-break bug (RED pin `ManualEditor.lineBreak.test.tsx`)

Why: sprint criterion requires a line break in Ручной режим, but the editor's `Document` holds `inline*` content with no paragraph to split on Enter, and simply re-enabling StarterKit `hardBreak` reintroduces a persisted stray trailing `<br>` (the reason it was disabled).

| Rejected | Why |
|----------|-----|
| Leave `hardBreak: false` | No schema node can represent a line break → text collapses onto one line. The bug itself. |
| Naive re-enable `hardBreak` | `domObserver` reparses ProseMirror's trailing-break cursor helper into a real trailing hardBreak node → `editor.getHTML()` (save payload, `useDocumentSave.ts:84`) persists an extra `<br>` on every non-empty save; 32 live-DOM tests regress. |
| B: block schema (`block+`, paragraphs) | Dismantles the mark-based design (heading3/blockquote/align/hr via `lineWrapMark`) and reopens bug-class 7.2 (stray `<blockquote>` node on every keystroke, `lineWrapMark.ts:3-12`). Large rewrite for a line break. |

**Chosen**: A′ — re-enable `hardBreak`, and add an editor `appendTransaction` that strips a `hardBreak` node sitting at the very end of the document. The trailing hardBreak is the sole corruption source; removing it makes `getHTML()` clean and dissolves the trailing-break helper cascade the 32 tests trip on. Line breaks in the middle of content are preserved. Keeps the mark architecture untouched.

## Model

- `ManualEditor` editor config: remove `hardBreak: false` from `StarterKit.configure` (hardBreak enabled).
- New extension/plugin (e.g. `stripTrailingHardBreak`): `appendTransaction` that, when the last node of the doc is a `hardBreak`, returns a transaction deleting it. Idempotent, runs on any docChanged.
- No change to `Document` content model (`inline*`), marks, save/init hooks, or DTOs.

## Edge Cases

| Case | Behavior |
|------|----------|
| Enter between two lines of text | `<br>` inserted and preserved; `getHTML()` = `a<br>b`. |
| Enter at the very end of content | Trailing hardBreak stripped by `appendTransaction`; no stray `<br>` persisted (matches the pre-existing "no stray break for non-empty content" invariant). |
| Multiple consecutive Enters at end | All trailing hardBreaks collapse away (only trailing ones; interior blanks between text are kept). |
| Empty document | No hardBreak node exists; strip is a no-op; placeholder still shown. |
| Reopen a saved document ending in `<br>` (legacy) | Init parses it; if it lands as a trailing hardBreak, first transaction strips it — self-healing, no persisted growth. |
