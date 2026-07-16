## align-design (2026-07-16)

**Surprise:** `heading3Mark.ts` reports 100% line/branch coverage while nothing verifies that a saved `<h3>` round-trips.
**Why:** `parseHTML` returns `{ tag: 'h3' }` — declarative data, not executable code, so its recorded hits are schema-build time, not document-parse time.
**Impact:** Any mark whose `parseHTML` is a bare tag rule needs an explicit round-trip test; its coverage number is not evidence either way.

## red-frontend-parseHTML (2026-07-16)

**Mistake:** Assumed the `<h3>` round-trip was broken because `h3` is in ProseMirror's hardcoded `blockTags` list (`prosemirror-model/dist/index.js:2683`), as `<pre>` was in 7.4 — a prior agent-review had also logged it as broken.
**Why wrong:** `blockTags` membership is not what broke `<pre>`; that failed because it matched a *wrapper* tag with no corresponding rule. A direct probe showed `<h3>` round-trips byte-exact.
**Correct location/approach:** Probe the round-trip directly before theorizing from the `<pre>` precedent.

**Quirk:** StarterKit's built-in `Heading` node stays enabled, so its `parseHTML` competes with `Heading3Mark`'s rule for `<h3>`; neither declares a priority and both render byte-identical output.
**Where:** `ManualEditor.tsx:95-102` (StarterKit config, `Document.extend({ content: 'inline*' })`), `lineWrapMark.ts:21`.
**Implication:** The mark wins only because the `inline*` doc schema makes the block node unreachable — an implicit tiebreak that flips silently if the schema ever gains block content; the H1/H2 toolbar buttons are already inert for this reason.
