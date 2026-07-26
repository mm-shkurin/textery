# Decision: Manual editor migrates to a full block-content schema

**Date**: 2026-07-26 **Scenarios**: E1.1, E1.2, E2.1, E6.1, E8.1, H10.1 (editor-extension points 1–8)

Points 1–8 need real block structure (multi-paragraph, H1–H3, lists, tables) that the deliberate `content: 'inline*'` + formatting-as-marks design cannot express; lists and tables have no mark representation at all.

| Rejected | Why |
|----------|-----|
| Additive block nodes + keep the custom marks at lower parse priority | Two live representations for `<h3>`/`<blockquote>` is the mark-vs-node ambiguity the premortem flagged; ProseMirror still reparents top-level inline into `<p>`, so the sibling reds break anyway — the back-compat marks buy nothing. |
| Minimal: nodes for headings/lists/tables only, blockquote/codeBlock/align stay marks | Inconsistent model; an `alignCenter` `<div>` mark is invalid inside a paragraph block; defers the same conflict without closing it. |

**Chosen**: Full StarterKit block model. `Document` uses `block+`; formatting that was a mark becomes a node/attribute; the bespoke line-break + placeholder machinery is retired for StarterKit standard equivalents. The ~40 sibling tests that hard-code inline-schema output are rewritten to block expectations as one coordinated red-rework that lands **with** the green migration (not silently in green, not as a separate behavior commit).

## Model

- **Document**: `content: 'block+'` (drop `Document.extend({ content: 'inline*' })`).
- **Enable StarterKit nodes** (currently disabled/overridden): `paragraph`, `heading` (levels 1–3), `bulletList`, `orderedList`, `listItem`, `blockquote`, `codeBlock`, `horizontalRule`, standard `hardBreak`.
- **Retire custom marks/nodes**: `Heading3Mark`, `BlockquoteMark`, `CodeBlockMark`, `HorizontalRuleNode`, `HardBreakNode`, `HardBreakKeymap`, `InlinePlaceholder` — replaced by their StarterKit counterparts. `AlignCenterMark` (`<div>` wrapper) → `textAlign` attribute on block nodes via `@tiptap/extension-text-align`.
- **Tables**: add `@tiptap/extension-table` (+ row/header/cell) — point 8, sequenced last.
- **Placeholder**: StarterKit/`Placeholder` extension on the empty top-level node (replaces the inline-emptiness plugin); keep the `Начните печатать…` copy and the `data-placeholder`/`is-editor-empty`/`aria-placeholder` surfaces the Selenium tests pin.
- **Toolbar actions**: H1/H2/H3 → `toggleHeading({level})`; blockquote/codeBlock/list → their node commands; `isActive` checks move from mark names to node/attr names. H1/H2 stop being inert.
- **Heading tiebreak**: resolved by construction — one owner (`heading` node); the `<h3>`-as-mark path is gone.
- **Serialize normalization**: strip a trailing empty `<p>` (ProseMirror's trailing-break paragraph) from saved HTML so E1.1's exact-innerHTML holds and the export filename/body (story 17) carries no spurious empty block.

## Edge Cases

| Case | Behavior |
|------|----------|
| Legacy inline-only document loads | Bare inline `content` auto-wraps into a single `<p>`; old mark-emitted `<h3>`/`<blockquote>` HTML parses into the corresponding heading/blockquote **node** (lossy-but-defined: mark → node, asserted by E1.2 / H10.1). No text is dropped. |
| Trailing empty paragraph on save | Stripped on serialize; a document that is genuinely empty serializes to empty content, not `<p></p>`. |
| Enter / line break | Standard `hardBreak` (Shift+Enter) inside a block; Enter splits the block (new paragraph/list item) — supersedes scenario 3.3 "approach A′"; its live save-payload test is re-asserted against the block model. |
| Inline marks inside blocks (bold, link, code, align) | Survive co-resident with block nodes (premortem #2); a mixed-content round-trip test is added, not just bare-text blocks. |
| ~40 inline-schema sibling assertions | Rewritten to block-wrapped/semantic expectations in the same work unit as the green migration; the rewrite is authorized by this ADR, so "tests read-only in green" does not block it for this scenario. |
| `heading3.parseHTML` asserts H3-as-mark | Retired/rewritten to assert the heading **node**; the mark it tested no longer exists. |
