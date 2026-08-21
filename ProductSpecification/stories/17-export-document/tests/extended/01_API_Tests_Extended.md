> These are additional edge case tests. Implement after core tests pass.

# Export document — API Tests (Extended)

Endpoint: `GET /api/v1/documents/{id}/export?format=pdf|docx`. Read-only.
Contract: `ProductSpecification/api-specs/documents_export.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A1 | id `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`, title `Отчёт по практике`, content `<p>Первый абзац.</p>` |
| Content limit | `1 000 000` characters (the save-path document content limit) |
| Render deadline | `EXPORT_RENDER_TIMEOUT_SECONDS`, default `30 s` |
| Error body shape | flat `{"error_code": "<CODE>", "message": "<text>"}` — see `backend/adapters/rest/src/error_handling/exception_handlers.py` |

## 1. Content Edge Cases

### TC-17-API-EXT-1.1 — A document at the content limit still exports

| Field | Value |
|---|---|
| Description | The largest content the save path accepts must still render; if the deadline is tuned to average documents, the legal maximum is the first thing that times out in production. |
| Preconditions | Document A11 exists, owned by account A, with content of exactly `1 000 000` characters (valid HTML paragraphs, saved through `PUT /api/v1/documents/{id}` so it is a legal row). |
| Test data | Document A11 id `9d2f6c05-4b81-4e17-a3c8-70b5e1f9a248`, content length exactly `1 000 000` characters, `format=pdf`, render deadline `30 s` |
| Steps | 1. `GET /api/v1/documents/9d2f6c05-4b81-4e17-a3c8-70b5e1f9a248/export?format=pdf` with account A's token.<br>2. Measure the wall-clock time of the call.<br>3. Save the body to `out.pdf` and open it. |
| Expected result | `200 OK`; `Content-Type: application/pdf`; the body's first five bytes are `%PDF-`; the call returns in under `30 s` (no `500` deadline abort); the file opens. |
| Status | Not run |

### TC-17-API-EXT-1.2 — Content with only whitespace exports to a valid file

| Field | Value |
|---|---|
| Description | Whitespace-only content is non-empty to the storage layer but empty to the renderer — the seam where a "nothing to render" branch returns zero bytes or a `500`. |
| Preconditions | Document A12 exists, owned by account A, with content `<p>   </p>\n\t ` (whitespace and empty markup only). |
| Test data | Document A12 id `1b8c47e3-92a0-4f65-8d1e-3c7a05b6f9d1`, `format=pdf` and `format=docx` |
| Steps | 1. Export document A12 as `pdf` and save the body.<br>2. Export document A12 as `docx` and save the body. |
| Expected result | Both answer `200 OK` with `Content-Disposition` starting `attachment;`; the PDF starts with `%PDF-` and has exactly one page; the DOCX starts with `PK` and opens; neither response body is zero bytes and neither call answers `4xx`/`5xx`. |
| Status | Not run |

## 2. Format Casing

### TC-17-API-EXT-2.1 — Format matching is exact, not case-folded loosely

| Field | Value |
|---|---|
| Description | The contract's enum is exactly `pdf` and `docx`, lowercase. A silently case-folding parser would accept values the spec rejects, so clients would ship uppercase values that break on the next strict deploy. |
| Preconditions | Document A1 exists and is owned by account A. |
| Test data | `format=PDF`, `format=Pdf`, `format=DOCX`, `format=pDf` |
| Steps | 1. `GET /api/v1/documents/7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913/export?format=PDF`.<br>2. Repeat with `?format=Pdf`.<br>3. Repeat with `?format=DOCX`.<br>4. Repeat with `?format=pDf`. |
| Expected result | All four behave identically to each other and match the documented rule: the enum is exact-lowercase, so each answers `422 Unprocessable Entity` with `Content-Type: application/json` and the flat error body (`error_code` `INVALID_FORMAT`); no file bytes and no `Content-Disposition` header in any of the four. |
| Status | Not run |
