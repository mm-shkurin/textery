# Manual input mode (non-AI document creation)

## Brief Description

Anonymous user picks a document type, skips AI generation entirely, and is dropped
into an empty document in the built-in editor to write and format the text by hand.

## Flow

1. User opens the type-select modal (reused from story #1): доклад/эссе/сочинение/реферат.
2. User opens the mode-select modal (reused from story #1): Ручной режим / Автоматический режим.
3. User picks Ручной режим.
4. System creates a `Document` directly (no `Generation` record, no LLM call) with the
   chosen `document_type` and empty content, and returns `document_id` immediately.
5. Client opens the document in the rich-text editor, empty, cursor ready.
6. User types content and applies basic formatting (headings, paragraphs, lists, bold,
   italic) via toolbar or shortcuts.
7. User triggers save (explicit action, not autosave — autosave is story #10).
8. Client sends the full document content to `PUT /documents/{id}`.
9. System persists the content and returns the saved state.
10. User can reopen the document later and continue editing (edit-after-save is in
    scope; AI-assisted doctoring of a manual document is not — story #10/future).

## Acceptance Criteria

- Picking Ручной режим creates a `Document` with `status=draft`, chosen `document_type`,
  empty `content`, and no linked `Generation` — no LLM call is made, ever.
- `POST /documents` (manual-create) returns 201 with `document_id` synchronously (no
  polling — this path has no async step).
- The editor renders an empty, immediately-editable surface for the new document.
- Toolbar/shortcuts apply exactly these formats: heading (levels covered by mockup),
  paragraph, bulleted list, numbered list, bold, italic — output is structured HTML
  matching those semantic elements, never raw unstyled text dumped in one block.
- `PUT /documents/{id}` persists the current editor content and is idempotent (same
  content saved twice yields the same stored state, no duplication).
- Saved content round-trips: reopening the document renders exactly what was saved,
  formatting included.
- Requests with an unsupported `document_type` are rejected with 422, matching story #1's
  contract.
- A save request for a `document_id` that doesn't exist returns 404, not a silent no-op.
- `POST /documents` (manual-create) accepts a client-supplied idempotency key (same
  convention as story #1's `Generation`); submitting the same key twice returns the
  existing `document_id` — never a second `Document` row.
- `content` past the pinned max length (see Validation Rules) is rejected with a clean
  4xx at that exact boundary — never truncated, never split mid multibyte-grapheme,
  never accepted unbounded.
- A save that lands after another save has already updated the same `document_id`
  (concurrent edit sessions) is rejected with 409 unless the client's base version
  matches current state — never a silent lost-update overwrite.
- A crafted `PUT /documents/{id}` body containing raw `<script>`/event-handler HTML
  (bypassing the editor UI entirely) is neutralized both in the persisted row and in
  any subsequent render — never stored or served as executable markup.
- A `PUT /documents/{id}` body containing `document_type`, `id`, or `status` is rejected
  or ignored on those fields specifically (each verified independently) — only `content`
  is ever written.
- 404/422/409/save-error response bodies expose a stable, generic client-facing error
  shape only — never a DB constraint message, internal id shape, or stack trace.
- When server-side sanitization alters submitted `content` (disallowed tags/attributes
  stripped), the save response and the round-trip read reflect the *sanitized* version —
  never a response that looks identical to the raw submission while storing something
  different.

## Validation Rules

| Field | Rule |
|-------|------|
| document_type | required at creation; fixed to one of the 4 story #1 values; any other value rejected (422) |
| content | required on save, may be empty string; max 200,000 characters (pinned here — story #1 does not itself bound `Document.content`, so this story owns the limit); rejected with 4xx at the boundary, never truncated mid-grapheme; server-side HTML sanitized before persist, allowlist-based (never a denylist) |

## Screen States

- **Type-select modal** — reused from story #1, no changes.
- **Mode-select modal** — reused from story #1; Ручной режим is now the active card
  (previously "скоро" placeholder), Автоматический stays as story #1 left it.
- **Empty editor** — blank document, toolbar visible, cursor focused, ready to type.
- **Editor with content** — user's typed/formatted text, toolbar reflects active
  formatting at cursor (e.g. Bold highlighted when cursor is in bold text).
- **Saved confirmation** — lightweight inline indicator (e.g. "Сохранено") after a
  successful save; no full-page transition.
- **Save error** — inline error, content stays in the editor (never cleared on failure).

## Core Requirements

- No `Generation` entity involved anywhere in this flow — manual documents are created
  directly, distinct code path from story #1's async generation.
- `Document` model is shared with story #1 — do not fork a separate manual-only document
  type; a manual document must remain eligible for future AI-assisted editing (per
  interview.md cross-story note) — i.e. no schema/field that hardcodes "no LLM ever" on
  the row itself.
- ~~No `User`/auth concept in this story's domain model (anonymous, same as story #1;
  story #7 dependency doesn't block).~~ **SUPERSEDED 2026-07-17 — see
  `decisions/document-ownership-decision.md`.** This rested on story #7 not existing;
  its `/login` has since landed and was verified live. A `Document` now has a NOT NULL
  `owner_id`, all three endpoints require a Bearer access token, and a document owned by
  another account answers 404 (never 403, which would confirm the id exists). Without an
  owner the endpoints are an IDOR: anyone holding a UUID reads and overwrites the row.
- Editor formatting output is structured content (e.g. sanitized HTML or a documented
  block-based JSON), never free-text with embedded formatting markers the client must
  regex-parse.
- Document content and any rendered formatting are served/rendered as sanitized output,
  never raw unescaped user HTML (stored XSS risk otherwise).
- `document_id` is a non-sequential opaque identifier (UUID), matching story #1's
  `generation_id` convention.
- Save is a plain synchronous request/response — no queue, no polling, no `Generation`
  status machine reused for this path.
- ~~`Document.generation_id` (or equivalent link field) is nullable — a manual `Document`
  has no `Generation` row, and story #1's existing `Document`-reading code paths must
  tolerate a null link without error (regression risk on a shared model).~~
  **CORRECTED 2026-07-17 — the premise is false.** Story #1 never built a `Document`: it
  has no such entity, no `documents` table, and `endpoints.md` records "No separate 'get
  document' endpoint — the completed document's content is returned" via `Generation`.
  So there is no shared model, no existing `Document`-reading code path, and nothing to
  keep null-tolerant. `generation_id` is therefore **omitted**, not nullable — scenario
  2.1's "no Generation is created or linked" is satisfied more strongly by the column's
  absence than by a null in it, and `tdd-rules.md` forbids preemptive fields. Adding the
  column later is additive and unblocked.
- A manual `Document` has no additional status machine beyond `draft` in this story's
  scope (no `completed`/`failed` — those are generation-only states); `PUT` never gates
  on status for a manual document. Broader lifecycle/transition rules stay story #1's
  concern.
- Manual-document creation is a single atomic insert; no `Generation` row is ever
  created on this path, under any failure branch (asserted, not just assumed).
- `PUT /documents/{id}` carries an optimistic-concurrency check (version/`updated_at`
  compare-and-swap) to guard against two concurrent editor sessions silently
  overwriting each other's edits.
- Anonymous, unauth'd `PUT`/`GET` on any guessable-but-unguessable `document_id` is an
  **accepted, temporary posture** (same as story #1's `Generation`) pending story #7 —
  explicitly not a defect to fix in this story, not silently out of scope either.
- Client disables the Save control while a save is in flight, and resolves out-of-order
  responses so the displayed save-status always reflects the latest edit, never a stale
  in-flight response.
- Unsaved edits lost on navigation/refresh (no autosave in this story) is an **accepted,
  temporary posture** — explicitly named here, not silently deferred; story #10 owns
  autosave/unsaved-state protection.
