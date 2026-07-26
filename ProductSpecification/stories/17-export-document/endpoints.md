# Export document — API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/documents/{document_id}/export?format=pdf\|docx | Render the document to PDF/DOCX and stream it (owner-scoped, read-only, in-memory) |

## Reused unchanged (story 5 / 7)

| Method | Path | From | Role |
|--------|------|------|------|
| GET | /api/v1/documents/{id} | story 5 | Source document (owner-scoped) |

## Additive schema change

Reads the `title` field on `Document` (shared additive migration with the story-5
extension — first session to land it adds the column). Used for the export filename.

## Notes

- Binary response, not JSON — `Content-Type` is `application/pdf` or the DOCX
  wordprocessingml type; `Content-Disposition: attachment` with an RFC 5987-encoded
  filename.
- Read-only: no polling, no document mutation, nothing persisted to disk.
- SSRF-safe: the PDF renderer's `url_fetcher` is disabled.
- Full contract: `ProductSpecification/api-specs/documents_export.yaml`.
