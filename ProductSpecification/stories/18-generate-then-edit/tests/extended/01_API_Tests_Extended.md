> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — API Tests (Extended)

Endpoint: `POST /api/v1/documents/from-generation`. Reused endpoints covered by stories 1 and 5.
Contract: `ProductSpecification/api-specs/documents_from_generation.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Generation G1 (completed, owned by A) | id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426`, `document_type` `доклад`, topic `История Москвы`, content `## Введение\n\nПервый абзац.` |
| Idempotency key | `Idempotency-Key: 6f3b91d2-4a58-4c7e-8d10-2e9f5b7a63c4` (1–128 chars, required) |
| Request body | `{"generation_id": "<uuid>"}` |
| Success body | `DocumentResponse` — `document_id`, `document_type`, `generation_id`, `title`, `status` (`draft`), `content` (sanitized HTML), `version`, `created_at`, `updated_at` |
| Error body shape | flat `{"error_code": "<CODE>", "message": "<text>"}` — see `backend/adapters/rest/src/error_handling/exception_handlers.py` |
| Content limit | `200000` Unicode code points |

## 1. Boundary & Edge

### TC-18-API-EXT-1.1 — Content exactly at the limit is accepted

| Field | Value |
|---|---|
| Description | An off-by-one at the limit turns the largest legal generation into a permanent `422` the user can never convert, and the boundary is exactly where `>` versus `>=` goes wrong. |
| Preconditions | Account A signed in; generation G3 exists, completed, owned by account A, whose **converted** (sanitized-HTML) content is exactly `200000` Unicode code points; no document is linked to G3 yet. |
| Test data | Generation G3 id `8c14a7f0-5d92-4b36-a17e-92f0c6b3d485`; converted content length exactly `200000` code points; `Idempotency-Key: 1f4d7a20-9b63-4e58-8c07-5d2a6f19b3c8` |
| Steps | 1. `POST /api/v1/documents/from-generation` with body `{"generation_id": "8c14a7f0-5d92-4b36-a17e-92f0c6b3d485"}` and the key above.<br>2. `GET /api/v1/documents/{document_id}` from the response and count the code points of `content`. |
| Expected result | Step 1 answers `201 Created` (never `422`) with a `DocumentResponse` whose `generation_id` is G3's id, `status` is `draft` and `version` is `1`; step 2 returns content of exactly `200000` code points, byte-identical to the converted content — nothing truncated. |
| Status | Not run |

### TC-18-API-EXT-1.2 — A grapheme straddling the limit is not split

| Field | Value |
|---|---|
| Description | If the limit is measured in one unit and enforced in another (bytes or UTF-16 units instead of code points), a multi-code-point grapheme sitting on the boundary is cut in half and a lone surrogate or a detached combining mark is stored. |
| Preconditions | Account A signed in; generation G4 exists, completed, owned by account A, whose converted content is `200001` code points with a multi-code-point grapheme (`👩‍🎓` ZWJ cluster, and `е` + U+0301) placed across the `200000` boundary. |
| Test data | Generation G4 id `b7e93c15-0a48-4d72-91f6-3e8b5c07a2d9`; boundary graphemes `👩‍🎓` and `е` + U+0301; pinned unit = Unicode code points; `Idempotency-Key: 3a8f52c1-6d70-4b94-a2e5-8f01c7b46d3e` |
| Steps | 1. `POST /api/v1/documents/from-generation` for generation G4 with the key above.<br>2. Read the response status and body.<br>3. `GET /api/v1/documents` (list account A's documents) and look for any document linked to G4. |
| Expected result | Step 1 answers `422 Unprocessable Entity` with `{"error_code": "CONVERTED_CONTENT_TOO_LONG", "message": "<text>"}` — the refusal is decided on code points, the pinned unit, not on bytes or UTF-16 units; step 3 shows no document with `generation_id` = G4's id, so no partial grapheme (no lone surrogate, no orphaned combining mark) was stored anywhere. |
| Status | Not run |

### TC-18-API-EXT-1.3 — An idempotency key outside the allowed length is refused

| Field | Value |
|---|---|
| Description | The key is the only thing preventing a duplicate document on a retry; accepting an out-of-range key means accepting one the store may truncate, silently colliding two different requests. |
| Preconditions | Account A signed in; generation G1 exists, completed, owned by account A, not yet converted. |
| Test data | Key of `129` characters (`a` × 129), and the empty key (`Idempotency-Key:` with no value); allowed range `1–128` characters; generation G1 id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426` |
| Steps | 1. `POST /api/v1/documents/from-generation` for generation G1 with `Idempotency-Key` set to `a` × 129.<br>2. Repeat with an empty `Idempotency-Key` value.<br>3. List account A's documents. |
| Expected result | Steps 1 and 2 both answer `422 Unprocessable Entity` with `{"error_code": "INVALID_IDEMPOTENCY_KEY", "message": "<text>"}`; step 3 shows no document linked to generation G1 — the refusal happens before any document is created. |
| Status | Not run |

## 2. Link Semantics

### TC-18-API-EXT-2.1 — A converted document reports its generation link on read

| Field | Value |
|---|---|
| Description | The link is written at conversion; if the read path does not project `generation_id`, the client cannot tell a generated document from a manual one and the provenance is lost after the first page load. |
| Preconditions | Account A signed in; generation G1 exists, completed, owned by account A; account A has converted it once. |
| Test data | Generation G1 id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426`; `Idempotency-Key: 6f3b91d2-4a58-4c7e-8d10-2e9f5b7a63c4` |
| Steps | 1. `POST /api/v1/documents/from-generation` for generation G1; record `document_id`.<br>2. `GET /api/v1/documents/{document_id}` with account A's token.<br>3. Read the `generation_id` field of the response body. |
| Expected result | Step 2 answers `200 OK`; the body's `generation_id` is exactly `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426` — the field is present on read, not only in the creation response, and matches the generation that produced the document. |
| Status | Not run |

### TC-18-API-EXT-2.2 — A manual document reports no generation link on read

| Field | Value |
|---|---|
| Description | The column is nullable and additive. If the read path defaults it to something non-null — an empty string, a zero uuid, or the document's own id — every blank document falsely claims a generation. |
| Preconditions | Account A signed in; a blank document is created from scratch through the normal create path (no generation involved). |
| Test data | Blank document D2 id `c58a0b47-91d3-4e26-8f71-2d0a6c9b4e13`, created via the manual create endpoint |
| Steps | 1. `POST /api/v1/documents` to create a blank document as account A and record its `document_id`.<br>2. `GET /api/v1/documents/c58a0b47-91d3-4e26-8f71-2d0a6c9b4e13`.<br>3. Read the `generation_id` field of the response body. |
| Expected result | Step 2 answers `200 OK`; `generation_id` is JSON `null` — not absent-by-error, not `""`, not `"00000000-0000-0000-0000-000000000000"`, and not the document's own id. |
| Status | Not run |
