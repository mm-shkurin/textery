# Generate → edit (unify generate + manual)

## Brief Description

User picks a document type, AI generates immediately (no mode-select modal), and the
completed result opens **editable** in the story-5 editor as a `Document`. Blank-from-
scratch stays as a secondary entry.

## Flow

1. User picks a document type in the type modal (mode-select modal removed).
2. Client starts AI generation immediately — `POST /generations` (async, story 1).
3. Client polls `GET /generations/{id}` until terminal state.
4. On `completed`, client calls `POST /documents/from-generation` with `{generation_id}`
   and an `Idempotency-Key`.
5. Backend validates the generation is `completed` and owned by the caller, converts its
   markdown-ish content → sanitized HTML, inserts a `Document` (linked `generation_id`),
   returns `{document_id, version, title, content}`.
6. Client auto-opens the editor loaded with that content — no extra click.
7. User edits and saves via `PUT /documents/{id}` (story 5, version-guarded).
8. Secondary path: "чистый лист" creates an empty `Document` via `POST /documents`
   (story-5 manual create, unchanged).

## Acceptance Criteria

- Type selection leads straight to generation — `ModeModal` is gone from the flow.
- `POST /documents/from-generation` on a `completed`, caller-owned generation returns 201
  with `document_id`, `version=1`, `title`, and sanitized HTML `content`.
- Conversion is idempotent AND race-safe: a DB **unique constraint on `generation_id`**
  makes a second insert (sequential replay OR two concurrent `POST`s across instances)
  fail atomically and return the existing `document_id` — never a second `Document` row.
- A generation not in `completed` (pending/in_progress/failed) → 409, no `Document`.
- An unknown/unmapped generation status → fails **closed** (409/422), never falls through
  to conversion.
- A generation absent or owned by another account → 404 (never 403), byte-identical for
  absent vs foreign, no `Document`.
- The created `Document` has `generation_id` set; a manual `POST /documents` leaves it
  null and **rejects** a client-supplied `generation_id`; both round-trip through `GET`.
- Server-owned fields in the conversion body (`title`, `id`, `status`, `version`, a spoof
  `generation_id`) are ignored/rejected per-field — only the authorized link and
  server-derived values are written.
- Converted content over the `Document.content` max → clean 4xx at the boundary; the
  limit is measured in **Unicode code points** (pinned), never truncated mid-grapheme.
  The **source** generation content is bounded *before* the parser runs, not only the
  HTML output.
- Multibyte content (Cyrillic + emoji + combining accent) round-trips byte-exact (after
  NFC) through `from-generation` → `GET`.
- Converted HTML is server-side allowlist-sanitized: `<script>`/event-handlers AND
  URL-scheme sinks (`javascript:`/`data:` links, `onerror` images) are neutralized in
  storage and every render. If the parser/sanitizer errors, conversion fails **closed** —
  no `Document`, nothing unsanitized stored.
- Non-markdown/plain-text/empty model output converts to valid sanitized HTML without
  crashing (degrade path), and emits a distinguishable operational signal.
- A conversion failure after the generation already `completed` emits a server-side
  error signal keyed by `generation_id` (operability); the happy path does not.
- After conversion the editor opens automatically from the `POST` response body (no
  re-read race); a generated document is fully editable and saves like a manual one.
- History (`GET /documents`) lists the `Document`; no duplicate "generation + document"
  pair is surfaced.
- Error bodies for 404/409/422 and the new parser-failure family expose a stable generic
  shape — a seeded internal sentinel (DB text, id shape, stack frame) never appears in
  the response or the logs.

## Validation Rules

| Field | Rule |
|-------|------|
| generation_id | required; must be a completed generation owned by the caller; else 404 (absent/foreign) or 409 (not completed) |
| Idempotency-Key | required on `POST /documents/from-generation`; same key returns the same `document_id`, never a duplicate |
| content (converted) | markdown→HTML→allowlist-sanitized before persist; max 200 000 chars, rejected at the boundary, never truncated |
| title | derived at conversion (from topic/type); editable later via story-5 save |

## Screen States

- **Type modal** — reused; leads directly to generation (no mode step).
- **Generating** — progress/polling state (reused `ChatWorkspace`/`DocArea` generating).
- **Auto-open editor** — on completion the surface becomes the editor with content loaded.
- **Editor with content** — story-5 editor, generated text editable, save/version states.
- **Conversion error** — inline error if `from-generation` fails; the generated text stays
  visible, user can retry, nothing is lost.
- **Blank editor** — secondary "чистый лист" entry, empty document.

## Core Requirements

- Frontend orchestrates conversion (poll sees `completed` → `POST /from-generation` →
  open editor). Backend does NOT create a `Document` inside generation completion — each
  usecase stays a single entry point (no usecase-calls-usecase).
- Client single-fires the auto-transition: an in-flight lock guarantees exactly one
  `POST /from-generation` even if two poll responses both observe `completed`; out-of-
  order poll responses bind to the latest.
- Poll loop and conversion retry carry jitter/backoff and an attempt cap (no lockstep
  thundering herd) — reconcile with story-1's `useGeneration` (it owns the poll).
- The editor auto-opened into an editable generated doc has unsaved-state protection
  (confirm-on-exit / draft) — reconcile with the story-5 editor spec.
- `Document.generation_id` is a new nullable column + migration; a rolling deploy means
  old story-5 code inserts/reads `Document` rows against the new column without failure,
  and existing `GET /documents` consumers tolerate the new `generation_id`/`title` fields.
- On-delete policy for the `generation_id` link is defined (FK behaviour under a future
  generation/account deletion) — no dangling reference left on the `Document`.
- `Generation` is retained after conversion (audit + original); `Document` is the source
  of truth. No generation row is deleted or mutated by conversion.
- Conversion is a single atomic insert of the `Document`; on any failure no partial
  `Document` and no mutation of the `Generation`.
- Markdown→HTML conversion runs server-side through the same `HtmlSanitizer` port as
  story-5 save; the client never receives unsanitized model output to render as HTML.
- New markdown-parser dependency must pass the CI `audit` (pip-audit) gate.
- `document_id` is an opaque UUID (matches story-1/5 convention).
- ACTION: verify real GigaChat output format on the stand before pinning the parser —
  the conversion must degrade safely if the output is plain text, not markdown.
