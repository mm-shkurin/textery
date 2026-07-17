# Manual input mode - API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/documents | Create an empty manual document (no LLM, no Generation) |
| GET | /api/v1/documents/{document_id} | Fetch a document (reopen/round-trip read) |
| PUT | /api/v1/documents/{document_id} | Save editor content (optimistic-concurrency guarded) |

## Notes

- No polling — this path is fully synchronous, unlike story #1's `Generation` flow.
- `version` is returned on create/read and required on save; a stale `version` on `PUT`
  returns 409 (lost-update guard, per hazard-scan group 3).
- `POST` requires the same client-supplied `Idempotency-Key` header convention as story
  #1's `POST /generations` (dup-submit guard, per hazard-scan group 2).
