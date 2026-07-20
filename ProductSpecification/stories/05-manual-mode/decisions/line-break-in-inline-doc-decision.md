# Decision: Line break (Enter) in the inline* editor document

**Date**: 2026-07-20 **Scenarios**: manual-mode line-break bug (RED pin `ManualEditor.lineBreak.test.tsx`)

Why: sprint criterion requires a line break in Ручной режим, but the editor's `Document` holds `inline*` content with no paragraph to split on Enter, and simply re-enabling StarterKit `hardBreak` reintroduces a persisted stray trailing `<br>` (the reason it was disabled).

| Rejected | Why |
|----------|-----|
| Leave `hardBreak: false` | No schema node can represent a line break → text collapses onto one line. The bug itself. |
| Naive re-enable `hardBreak` | `domObserver` reparses ProseMirror's trailing-break cursor helper into a real trailing hardBreak node → `editor.getHTML()` (save payload, `useDocumentSave.ts:84`) persists an extra `<br>` on every non-empty save; 32 live-DOM tests regress. |
| B: block schema (`block+`, paragraphs) | Dismantles the mark-based design (heading3/blockquote/align/hr via `lineWrapMark`) and reopens bug-class 7.2 (stray `<blockquote>` node on every keystroke, `lineWrapMark.ts:3-12`). Large rewrite for a line break. |

**Chosen**: A′ — enable `hardBreak` and stop the stray trailing `<br>` **at its two origins** rather than deleting it after the fact. Line breaks in the middle of content are preserved; the mark architecture is untouched.

> **Implementation note (green, commit — supersedes the first draft of this ADR).** The originally-planned `appendTransaction` delete-strip is **unviable here** and was proven so empirically: its own delete re-renders ProseMirror's trailing-break cursor helper, and the forced synchronous `domObserver.flush()` (`editorDomSync.ts`) reparses that helper into a fresh trailing hardBreak inside the *same* dispatch — an unbreakable strip↔reparse loop that OOM-crashes. A debug probe also showed the stray break is *primarily a schema ghost-filler*, not the reparsed helper. So the fix removes both **sources** instead of the symptom.

## Model

- `ManualEditor.tsx`: keep `hardBreak: false` in `StarterKit.configure` (avoids a duplicate schema-name collision) and register a dedicated `HardBreakNode` that replaces it — hardBreak is functionally enabled. `Document` content model (`inline*`), marks, save/init hooks, DTOs unchanged.
- `hardBreakNode.ts` — `HardBreak.extend` with (a) a **required** `marker` attribute: `hasRequiredAttrs()` becomes true, disqualifying hardBreak from the `inline*` schema's `ContentMatch.defaultType`, so ProseMirror never auto-injects it as ghost filler (same class as `horizontalRuleNode.ts`); (b) a higher-priority parse rule that `ignore`s `br.ProseMirror-trailingBreak` (the cursor helper), so `domObserver.flush()` never reads it into the doc. A real user break renders as a bare `<br>` (no helper class), so interior breaks survive; only the stray trailing one is prevented.
- `hardBreakKeymap.ts` — binds plain **Enter** and **Shift-Enter** to insert a hardBreak (via `insertContent({type:'hardBreak', attrs:{marker:'br'}})`, since `setHardBreak()` throws on the now-required attr). In an `inline*` doc the default Enter keymap has no block to split, so without this plain Enter is a no-op.

## Edge Cases

| Case | Behavior |
|------|----------|
| Enter between two lines of text | `<br>` inserted and preserved; `getHTML()` = `a<br>b`. |
| Enter at the very end of content | Trailing hardBreak stripped by `appendTransaction`; no stray `<br>` persisted (matches the pre-existing "no stray break for non-empty content" invariant). |
| Multiple consecutive Enters at end | All trailing hardBreaks collapse away (only trailing ones; interior blanks between text are kept). |
| Empty document | No hardBreak node exists; strip is a no-op; placeholder still shown. |
| Reopen a saved document ending in `<br>` (legacy) | Init parses it; if it lands as a trailing hardBreak, first transaction strips it — self-healing, no persisted growth. |
