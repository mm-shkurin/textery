# Story 10 — spec phase journey

## story (2026-08-02)

**Surprise:** A font WeasyPrint cannot resolve produces a successful 200 PDF laid out in
substituted metrics, not an error.
**Why:** `_blocked_url_fetcher` raises per resource, but WeasyPrint catches per-resource
fetch failures, logs, and continues rendering.
**Impact:** Any scenario relying on the bundled face must assert the failure explicitly —
"the export succeeded" is not evidence the right font was used.

## mockups (2026-08-02)

**Decision:** The customer design's "Добавить страницу" rail action becomes "Вставить
разрыв страницы"; the rail is navigation only.
**Why:** Pages are derived from content height, so a page cannot be created by hand — the
original control promised a model the story deliberately does not build.
**Where applied:** `mockups/*/01-editor-paginated.html` rail, and UI scenario 8.2, which
asserts no control claims to add or delete a page.

## discussion (2026-08-02)

**Mistake:** Ran the whole spec phase (`/interview` onward) without first checking git for
existing work, overwriting an untracked `10-editor-pages/` folder a prior session had
already populated.
**Why wrong:** `/interview` requires warning before regenerating an existing
`interview.md`; untracked overwritten files have no history to recover from.
**Correct location/approach:** Read `git status` for the story folder before the first
spec skill, and diff against what exists rather than regenerating.
