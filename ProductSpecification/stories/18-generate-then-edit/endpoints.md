# Generate → edit — API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/documents/from-generation | Convert a completed generation into an editable Document (owner-scoped, idempotent, race-safe) |

## Reused unchanged (story 1 / story 5)

| Method | Path | From | Role in this flow |
|--------|------|------|-------------------|
| POST | /api/v1/generations | story 1 | Start AI generation (async) |
| GET | /api/v1/generations/{id} | story 1 | Poll until `completed` |
| GET | /api/v1/documents/{id} | story 5 | Reopen the converted document |
| PUT | /api/v1/documents/{id} | story 5 | Save edits (version-guarded) |
| POST | /api/v1/documents | story 5 | Secondary "чистый лист" blank entry |
| GET | /api/v1/documents | story 5 | History listing (shows the Document, not the generation) |

## Additive schema changes (shared DocumentResponse)

`generation_id` (nullable uuid) and `title` (string) are added to the shared
`DocumentResponse` used by `documents_create.yaml`, `documents_get.yaml`,
`documents_save.yaml`. Additive only — existing consumers must tolerate the new fields.
The backend session owns the `title` column + accepting it on `POST`/`PUT` (see the
story-5-extension scope, point 4). A client-supplied `generation_id` on the manual
`POST /documents` is rejected.

## Notes

- The only NEW endpoint is `POST /documents/from-generation`. Everything else is reuse —
  this is the decoupling seam between the backend and frontend sessions.
- Idempotency + concurrency are closed by a single UNIQUE constraint on
  `Document.generation_id`; the endpoint returns 200 (existing document) on a replay or a
  lost race, 201 on first conversion.
- No polling on this endpoint — synchronous request/response. The generation poll is the
  story-1 endpoint above.
- Full contract: `ProductSpecification/api-specs/documents_from_generation.yaml`.
