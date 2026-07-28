# AI chat editing of an existing document - API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/documents/{document_id}/ai-edits | Queue an AI edit of the document (idempotent, one active edit per document) |
| GET | /api/v1/documents/{document_id}/ai-edits/{edit_id}/stream | SSE stream of edit events (`chunk`, then exactly one `done`/`error`/`cancelled`), replayable via `Last-Event-ID` |
| GET | /api/v1/documents/{document_id}/ai-edits/{edit_id} | Edit state — polling fallback when SSE is unavailable |
| POST | /api/v1/documents/{document_id}/ai-edits/{edit_id}/cancel | Terminalize a non-terminal edit as `cancelled` |
| GET | /api/v1/documents/{document_id}/messages | Chat history for the document (keyset-paginated) |
| GET | /api/v1/documents/{document_id}/revisions | Revision history (keyset-paginated, no content in the list view) |
| POST | /api/v1/documents/{document_id}/revisions/{revision_number}/restore | Restore revision `n` as a NEW version (nothing is destroyed) |

## Reused unchanged (story 5 / 7 / 18)

| Method | Path | From | Role in this flow |
|--------|------|------|-------------------|
| GET | /api/v1/documents/{id} | story 5 | Load content + version after `done` |
| PUT | /api/v1/documents/{id} | story 5 | Manual version-guarded save; races the AI edit on the same `base_version` |

**A manual save during a live AI edit is ALLOWED, not blocked.** `PUT /documents/{id}` is
story 5's endpoint and this story does not change it: it succeeds if its `version` matches,
and the in-flight AI edit then loses its own CAS at apply time and ends terminal with the
version-conflict code, refunded, having written no revision. The one-active-mutation 409
covers a second `POST /ai-edits` and a `restore` — the two operations this story owns — not
the manual save. Blocking the save instead would mean a hung edit locks the user out of
their own document for the whole edit deadline, which is exactly what the cancel button and
the deadline exist to prevent.
| POST | /api/v1/documents/from-generation | story 18 | Produces the document being edited |

## Notes

- **`cancel` is not in `interview.md`'s endpoint table but is required by it.** The
  interview mandates a visible cancel button and a `cancelled` terminal state
  (`19_AiChatEditing_Criteria.md`, "Edit lifecycle"), which no other endpoint provides.
  Modelled as `POST .../cancel`, not `DELETE`, because nothing is deleted — the edit
  transitions to an absorbing terminal state and its event rows stay replayable.
- **All seven endpoints share one 404 body.** Absent document, foreign document, foreign
  `edit_id`, and foreign/unknown `revision_number` are byte-identical — the path document
  id is authoritative, never decorative. Never 403. The 401 body is likewise identical
  across all seven.
- **No SSE event carries HTML.** Chunks are plain text and are rendered as text; on the
  terminal event the client re-fetches `GET /documents/{id}` for the sanitized, persisted
  content. Rendering concatenated chunk text as markup is the stored-XSS path this split
  closes, so the contract gives the client no HTML to render early even by accident.
- **SSE terminal kinds are `done` / `error` / `cancelled`** — exactly the terminal values
  of `AiEditResponse.status`. A cancel is a user action, not a failure, so it is not
  folded into `error`: the client unfreezes and reverts without an error banner or retry.
- **Reconnect always terminates.** `GET /ai-edits/{edit_id}` hands the client `last_seq`
  to reconnect with, and `Last-Event-ID` replays strictly *after* that seq — which would
  filter out the terminal event itself. The stream therefore re-emits the terminal event
  unconditionally on a terminal edit. Without that carve-out the documented recovery path
  is a guaranteed silent hang.
- **Revision origin is explicit.** A document with no history gets a baseline revision on
  its first mutation: revision 1 holds the pre-mutation content, revision 2 the result.
  Otherwise the first AI edit could never be rolled back.
- **`limit` is clamped, never rejected**, and neither list endpoint declares an `order`
  parameter — ordering is fixed server-side (messages oldest-first, revisions
  newest-first).
- **Shape errors are 422, semantic errors are 400**, uniformly with `documents_save.yaml`.
  `selection: null` is a shape violation (422) and is *not* the same input as an omitted
  `selection`, which means whole-document.
- **`selection` offsets are Unicode code points**, tied to `base_version` — not UTF-16
  units and not bytes. Same unit as `DocumentContent`'s 200 000 limit.
- The stream endpoint is the only non-JSON response (`text/event-stream`); its event
  payloads are JSON objects documented as schemas in `documents_ai_edits_stream.yaml`.
- Full contracts: `ProductSpecification/api-specs/documents_ai_edits_*.yaml`,
  `documents_messages_list.yaml`, `documents_revisions_list.yaml`,
  `documents_revisions_restore.yaml`.
