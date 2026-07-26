# Story 5 — Editor extension ("full manual mode", points 1–8)

Extension of story 5's editor for comfortable real-document work, driven by
`../../decisions/editable-generated-docs-scope.md`. This is an addendum to
`05_ManualMode.md`, not a new story — same `Document`, same `PUT /documents/{id}`. It also
unblocks story 18's frontend (a generated multi-paragraph document cannot open in the
current inline-only editor).

## Root blocker (point 0/1)

The editor schema is `inline*` today — block commands (paragraphs, headings, lists) are
inert. Everything below stands on migrating to **block content**. This is the first work
unit; nothing else can land before it.

## Scope (points 1–8)

1. **Block schema** — paragraphs + real H1/H2/H3 as block nodes (not marks).
2. **Lists** — bulleted and numbered.
3. **Autosave** — debounced over the existing `PUT /documents/{id}`; no backend change.
4. **Document title** — editable title field; feeds the export filename. Needs a `title`
   column on `Document` + accept on `POST`/`PUT` (backend, shared with stories 17/18 —
   first session to land the column owns it).
5. **Undo/redo on the block schema** — verify history under block nodes.
6. **Paste sanitize** — clean pasted Word/browser HTML on the client (allowlist,
   consistent with the backend `HtmlSanitizer`).
7. **Word / character count** — objём matters for доклад/эссе.
8. **Tables** — heaviest; sequence last.

Out of scope: images (needs file storage), full hotkey parity.

## Acceptance Criteria

- The editor holds multi-paragraph block content: paragraphs, H1–H3, bulleted and
  numbered lists round-trip through save and reload as the correct semantic HTML.
- Autosave persists edits without an explicit click, debounced; a save-in-flight indicator
  and a saved/failed state are shown; a failed autosave never clears the editor.
- Out-of-order autosave responses resolve so the shown status reflects the latest edit.
- A document title can be set and edited; it round-trips through save/reload and is used as
  the export filename (story 17).
- `title` is bounded (max length pinned) and rejected cleanly at the boundary; server-owned
  fields on `POST`/`PUT` remain ignored (story-5 posture).
- Pasted rich content is sanitized on the client to the allowlist before it enters the
  document — script/handlers/dangerous URL schemes never land in the editor; the server
  re-sanitizes on save regardless (defence in depth).
- Undo/redo restore block structure correctly, not just inline text.
- The word/character count reflects the current content, counted in Unicode grapheme
  clusters (a combining accent or emoji counts as one), and updates as the user types.
- Tables can be inserted, edited, and round-trip through save/reload.

## Validation Rules

| Field | Rule |
|-------|------|
| content | block-structured sanitized HTML; existing 200 000 code-point limit (story 5) |
| title | optional; max length pinned (e.g. 200 chars); trimmed; rejected at boundary; sanitized (no markup) |

## Core Requirements

- Block-schema migration must preserve existing inline-only documents on load (no data
  loss reading an old `content`).
- Autosave reuses `PUT /documents/{id}` with the version guard — a stale autosave is
  rejected (409) and reconciled, never a silent lost update.
- Client paste-sanitize is defence in depth, NOT a replacement for server-side
  sanitization on save.
- `title` column is a nullable additive migration (shared with stories 17/18); old code
  and existing documents tolerate its absence/null (rolling deploy).
- Word/char count is client-side only, no endpoint.
- This is a frontend-owned work stream (session C) except the `title` backend column
  (session A). See the scope-lock doc for the session split and the accepted B/C
  frontend-collision-resolved-at-merge posture.

## Hazard-scan record

Scanned 2026-07-26 against catalogue **Groups 1–8** (spec + tests). Key gaps folded into
`tests/08_Editor_Extension_Hazard_Tests.md`: content-only autosave must not wipe the title
(omit-vs-null), out-of-order autosaves preserve newest content, autosave failure taxonomy
(transient backoff/cap vs re-auth), save-storm coalescing, version fail-closed, mass
assignment with `title` added, legacy load-edit-save without content loss, NFC round-trip,
dirty-state exit guard, rolling-deploy `title` column. Seams: title→export-filename header
injection (story 17), IDOR on the write endpoints (base story 5), paste-size / content-cap
on block content (base story 5). Re-scan if a Group 9+ lands while open.
