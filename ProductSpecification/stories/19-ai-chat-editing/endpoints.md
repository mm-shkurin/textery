# AI chat editing of an existing document - API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/documents/{document_id}/ai-edits | Queue an AI edit of the document (idempotent, one active edit per document) |
| GET | /api/v1/documents/{document_id}/ai-edits/{edit_id}/stream | SSE stream of edit events (`chunk`, then exactly one `done`/`error`), replayable via `Last-Event-ID` |
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
| POST | /api/v1/documents/from-generation | story 18 | Produces the document being edited |

## Notes

- **`cancel` is not in `interview.md`'s endpoint table but is required by it.** The
  interview mandates a visible cancel button and a `cancelled` terminal state
  (`19_AiChatEditing_Criteria.md`, "Edit lifecycle"), which no other endpoint provides.
  Modelled as `POST .../cancel`, not `DELETE`, because nothing is deleted — the edit
  transitions to an absorbing terminal state and its event rows stay replayable.
- **Six endpoints share one 404 body.** Absent document, foreign document, foreign
  `edit_id`, and foreign/unknown `revision_number` are byte-identical — the path document
  id is authoritative, never decorative. Never 403.
- **`selection` offsets are Unicode code points**, tied to `base_version` — not UTF-16
  units and not bytes. Same unit as `DocumentContent`'s 200 000 limit.
- The stream endpoint is the only non-JSON response (`text/event-stream`); its event
  payloads are JSON objects documented as schemas in `documents_ai_edits_stream.yaml`.
- Full contracts: `ProductSpecification/api-specs/documents_ai_edits_*.yaml`,
  `documents_messages_list.yaml`, `documents_revisions_list.yaml`,
  `documents_revisions_restore.yaml`.
