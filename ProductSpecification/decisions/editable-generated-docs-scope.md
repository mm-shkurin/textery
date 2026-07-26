# Decision — Editable generated documents + export (3 parallel sessions)

**Date:** 2026-07-25. **Status:** accepted, drives the next spec+build wave.

Cross-story decision spanning story 5 (existing) plus two new stories. Recorded here
because no single story owns it. Individual stories carry their own interview/spec; this
file is the shared map so the three parallel sessions do not collide.

## The feature, in one line

User picks a document type → AI generates → the result opens **editable** in the story-5
editor → user edits → exports to PDF/DOCX. The mode-select modal (ручной/авто) is removed.

## Session split (3 sessions, decided with user)

| Session | Worktree | Owns files | Scope |
|---|---|---|---|
| **A — backend** | `textery-be` | `backend/`, `acceptance/tests/backend/` | export endpoint (html→pdf/docx), `POST /documents/from-generation`, `title` field on `Document` |
| **B — frontend export** | `textery-fe` | `frontend/`, `acceptance/tests/frontend/` | export button + blob download + states |
| **C — frontend story 5** | *new worktree* | `frontend/` (editor), story-5 progress files | editor upgrade, points 1–8 below |

**Known collision, accepted:** sessions B and C both touch `frontend/` — the export
button lives in the editor toolbar that session C rewrites. Save/merge conflicts on the
toolbar/editor files are **resolved at merge time**, not avoided by serialization
(user's call 2026-07-25). Keep edits small and commit often to shrink the conflict
surface. This is a deliberate exception to CLAUDE.md File Ownership (which assumes one
frontend session per story).

## Story 5 editor — the "full manual mode" scope (points 1–8)

Beyond what already ships (inline-only formatting: bold/italic/strike/underline/inline
code/H3-mark/quote-mark/hr/code-block-mark/center/link/undo/redo/hard-break):

0. **Block schema migration** — the root blocker. Editor is `inline*` today; block
   commands are inert. Migrate to block content so everything below is possible. Every
   other point stands on this. (Code comment already flags this as "a separate story".)
1. **Block schema** — paragraphs + real H1/H2/H3 as block nodes.
2. **Lists** — bulleted + numbered (removed with the inline schema; restore).
3. **Autosave** — debounce over the existing `PUT /documents/{id}`; no backend change.
   Removes the current "edits lost on refresh" posture.
4. **Document title** — editable title field; also feeds the export filename. Needs a
   `title` column on `Document` + accept in `POST`/`PUT` → **session A** owns the backend
   half, **session C** the UI.
5. **Undo/redo on block schema** — verify history behaves under block nodes.
6. **Paste sanitize** — clean pasted Word/browser HTML on the client (reuse the backend
   allowlist convention).
7. **Word/char count** — objём matters for доклад/эссе.
8. **Tables** — heaviest item; in scope but sequence last.

Out of scope for now: images (needs file storage — separate infra), full hotkey parity.

## New stories

- **Story 17 — Export to PDF/DOCX.** Backend renders the file on the fly from stored
  sanitized HTML, streams it (no disk — multi-instance rule). `GET
  /documents/{id}/export?format=pdf|docx`, Bearer, owner-scoped (404 foreign/absent).
  DOCX via python-docx/htmldocx, PDF via WeasyPrint. **Security:** disable the renderer's
  network fetch (`url_fetcher`) so an `<img src>` in content can't SSRF; filename derived
  from title with RFC 5987 encoding for Cyrillic, header-injection-safe. New deps must
  pass the CI `audit` (pip-audit) gate.
- **Story 18 — Generate → edit (unify, drop mode modal).** On generation complete, convert
  the generation to a `Document`: `POST /documents/from-generation {generation_id}`
  (Idempotency-Key, owner-scoped, 409/422 if generation not completed), converting the
  markdown-ish generation content → sanitized HTML. Frontend removes `ModeModal`, wires
  type → generate → open-in-editor. The story-5 editor is the edit surface (reused, not
  rebuilt). Blank-from-scratch entry stays available (reuses story-5 manual create) as a
  secondary path.

## Decoupling contract (what lets the sessions run independently)

The API contracts are the only coupling. Once `api-spec` pins them, backend implements,
frontend mocks + calls:

- `GET /api/v1/documents/{id}/export?format=pdf|docx` → binary + `Content-Disposition`
- `POST /api/v1/documents/from-generation` → `{document_id, version, content, title}`
- `title` added to `POST`/`PUT /documents` and `GET` response

## Lifecycle note

Each of story 5-extension / 17 / 18 still needs its own `/interview → /story → /mockups →
/api-spec → /test-spec` before scenario TDD. This doc is the pre-interview scope lock, not
a substitute for those.
