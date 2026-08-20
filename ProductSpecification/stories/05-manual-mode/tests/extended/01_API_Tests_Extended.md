> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — API Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `document_type` `реферат`, `content` `<p>Первый абзац.</p>`, `version` `2`, no linked generation |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |

## 1. Idempotency Edge Cases

### TC-05-API-EXT-1.1 — Different idempotency keys for otherwise-identical create requests create separate documents

| Field | Value |
|---|---|
| Description | The de-duplication must key on the header, not on the body. Keying on the body would refuse a user their second document of the same type. |
| Preconditions | Account A signed in; no document exists for account A. |
| Test data | Both calls send body `{"document_type": "реферат"}`; keys `Idempotency-Key: 3f0c8a9e-2b41-4d77-9c6a-b5e1d2704f88` and `Idempotency-Key: 6a2d5b71-8e93-4c05-b1fa-0d47e83c9152` |
| Steps | 1. `POST /api/v1/documents` with the first key.<br>2. `POST /api/v1/documents` with the identical body and the second key.<br>3. Count the documents owned by account A. |
| Expected result | Both answer `201 Created`, neither `200`; the two `document_id` values differ; account A owns exactly two documents. |
| Status | Not run |

## 2. Save Edge Cases

### TC-05-API-EXT-2.1 — Saving with an empty content string is accepted

| Field | Value |
|---|---|
| Description | Clearing a document is a legitimate edit, not an error. Treating `""` as "field missing" would refuse the save or leave the old text in place. |
| Preconditions | Document A1 exists with `content` `<p>Первый абзац.</p>` at `version` `2`. |
| Test data | Body `{"content": "", "version": 2}` |
| Steps | 1. `PUT /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` with that body.<br>2. `GET /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`. |
| Expected result | `200 OK` with `version` `3`; step 2 returns `content` exactly `""` — not `null`, and not the previous `<p>Первый абзац.</p>`. |
| Status | Not run |

### TC-05-API-EXT-2.2 — A save request missing the version field is rejected

| Field | Value |
|---|---|
| Description | `version` is required by the contract; defaulting an absent one to the current value would turn every such save into an unconditional overwrite with no concurrency check at all. |
| Preconditions | Document A1 exists at `version` `2`. |
| Test data | Body `{"content": "<p>Без версии</p>"}` — no `version` key |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that body.<br>2. `GET /api/v1/documents/{A1}`. |
| Expected result | `422 Unprocessable Entity` with `{"error_code": "INVALID_VERSION", …}` — never `200` and never `409`; step 2 shows `content` still `<p>Первый абзац.</p>` at `version` `2`. |
| Status | Not run |

## 3. Nullable Link Compatibility

### TC-05-API-EXT-3.1 — Existing story #1 document-reading paths tolerate a manual document's null generation link

| Field | Value |
|---|---|
| Description | Story #1's readers were written when every document had a generation. A non-null assumption there turns a manual document into a `500` on a shared read path. |
| Preconditions | Document A1 exists with no linked `Generation` row (`generation_id` is `NULL`), owned by account A. |
| Test data | Document A1 id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`; the story #1 document-reading endpoints (`GET /api/v1/documents/{id}`, `GET /api/v1/projects`) |
| Steps | 1. `GET /api/v1/documents/{A1}` through the story #1 read path.<br>2. Read document A1 through the project/document listing that story #1 ships. |
| Expected result | Both answer `200 OK` — no `500` and no `INTERNAL_ERROR`; the missing generation link is represented as absent (`null`/omitted `generation_id`), not as an error, and every other field of document A1 is returned normally. |
| Status | Not run |

### TC-05-API-EXT-3.2 — Story #1's generation-completion path can never mutate a manual document's status

| Field | Value |
|---|---|
| Description | A completion handler that looks up the document by id and writes `status` without verifying a matching `Generation` would flip a hand-written draft to `completed` — or to `failed` — on a stray callback. |
| Preconditions | Document A1 exists with `status` `draft` and no `Generation` row referencing it. |
| Test data | Invoke story #1's generation-completion/status-update path against `document_id = 3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, for which no `Generation` exists |
| Steps | 1. Invoke the completion path against document A1's id.<br>2. Read the outcome of that invocation.<br>3. `GET /api/v1/documents/{A1}` and read `status`. |
| Expected result | Step 2 shows the operation was rejected or was a no-op — it did not find a matching `Generation` and did not proceed; step 3 shows `status` still `draft`, never `completed` and never `failed`. |
| Status | Not run |
