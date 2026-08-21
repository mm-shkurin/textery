<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — Security Tests (Extended)

Stack-aware scenarios for the conversion endpoint. Generic auth (401), headers, CORS, and
HTTPS are covered globally and omitted here.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Generation G1 (completed, owned by A) | id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426`, topic `История Москвы` |
| Generation G2 (completed, owned by B) | id `a91c6b34-2d70-4f85-9c1e-6b04a7f2d539` |
| Conversion request | `POST /api/v1/documents/from-generation`, body `{"generation_id": "<uuid>"}`, header `Idempotency-Key` |
| Error body shape | flat `{"error_code": "<CODE>", "message": "<generic text>"}` |
| Not-found body | `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` |

## 1. Injection Variants

### TC-18-SEC-EXT-1.1 — Nested and encoded markup does not survive sanitization

| Field | Value |
|---|---|
| Description | A sanitizer applied once, before the markdown renderer, can be defeated by markup that only becomes executable after rendering, or by HTML-entity encoding that decodes into a tag on the second pass. The stored content is what every later read and export replays. |
| Preconditions | Account A signed in; generation G5 exists, completed, owned by account A, with the provider content below. |
| Test data | Generation G5 id `2e7c40b8-9f13-4a65-8d02-71b5e6c3a94f`; provider markdown ``Обычный текст\n\n<div><img src=x onerror="alert(1)"></div>\n\n&lt;script&gt;alert(2)&lt;/script&gt;\n\n[ссылка](javascript:alert(3))\n\n`<svg/onload=alert(4)>`\n\n<a href="&#106;avascript:alert(5)">клик</a>``; `Idempotency-Key: 9c3e15a7-b280-4d64-a1f8-07e2b5c69d31` |
| Steps | 1. `POST /api/v1/documents/from-generation` for generation G5.<br>2. `GET /api/v1/documents/{document_id}` and read the stored `content` verbatim.<br>3. Open the document in the editor and read the rendered DOM. |
| Expected result | Step 1 answers `201 Created`; the stored `content` in step 2 contains the text `Обычный текст` but no `<script>` tag, no `onerror=`/`onload=` attribute and no `javascript:` URL — in raw or entity-encoded form (a decode pass over the stored content yields none of them either); in step 3 the DOM contains no `script` element and no event-handler attribute, and no alert fires. |
| Status | Not run |

## 2. Idempotency Abuse

### TC-18-SEC-EXT-2.1 — A replayed key from another account does not disclose the document

| Field | Value |
|---|---|
| Description | If the idempotency key is scoped globally rather than per account, replaying a guessed or leaked key returns the first account's stored response — handing a stranger another user's document id, title and full content. |
| Preconditions | Account A signed in and has converted generation G1 with the key below, receiving document D3; account B signed in with its own token; account B owns generation G2. |
| Test data | Shared key `Idempotency-Key: 4b71e8d0-2c96-4f13-a507-8e60d9b34c27`; generation G1 id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426` (owned by A); generation G2 id `a91c6b34-2d70-4f85-9c1e-6b04a7f2d539` (owned by B); document D3 = account A's converted document |
| Steps | 1. As account A, `POST /api/v1/documents/from-generation` for generation G1 with the shared key; record document D3's `document_id` and `content`.<br>2. As account B, send the same request body (`generation_id` = G1) with the same key.<br>3. As account B, send `generation_id` = G2 with the same key.<br>4. As account B, `GET /api/v1/documents/{D3 document_id}`. |
| Expected result | Step 2 answers `404 Not Found` with exactly `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` — generation G1 is not account B's, and the answer never replays account A's `201` body; step 3 succeeds on its own merits (`201 Created`) with a **different** `document_id` than D3, proving the key is scoped per account rather than globally; step 4 answers `404`; account B's responses contain none of document D3's `document_id`, `title` or `content`. |
| Status | Not run |
