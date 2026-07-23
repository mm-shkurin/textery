# Scenario 2.1 — Freshly created document shows an empty, ready-to-type editor (journey summary)

## green-selenium (2026-07-22)

**Surprise:** the empty-editor placeholder renders NOWHERE in the live app — a fresh document's content area is exactly `<br class="ProseMirror-trailingBreak">`, with no `.me-placeholder` element and no `data-placeholder` attribute.
**Why:** Tiptap's `Placeholder` extension decorates an empty NODE, and the doc schema is `Document.extend({ content: 'inline*' })` — there is no paragraph node to carry the decoration, so it silently no-ops; `.me-placeholder` exists only in `ManualEditor.css` and is rendered by nothing.
**Impact:** scenario 2.1's `green-selenium` stays skipped on this real defect (not infrastructure); no jsdom test asserts the placeholder, so a green suite covered a missing feature — a fourth instance of this story's "a green suite is not evidence".
