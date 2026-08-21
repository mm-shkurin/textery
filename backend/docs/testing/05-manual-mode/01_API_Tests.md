<!-- COPIED FILE. Source of truth: ProductSpecification/stories/05-manual-mode/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Manual input mode (non-AI document creation) — API Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with request validation (no infrastructure needed), then the happy-path create,
> then the mandatory re-run-safety guard, then read (which depends on a document
> existing), then save validation, then save happy-path/concurrency, then save security
> guards.

**Amended 2026-07-17** — see `decisions/document-ownership-decision.md`. The original text
read: *"No prerequisite-resource guards apply to this story — `POST /documents` has no
parent resource that must exist first"*. That is no longer true. Every scenario below now
runs as an **authenticated owner**: each endpoint requires `Authorization: Bearer
<access_token>`, so every test's precondition implies a register → verify → login bootstrap,
and the account is `POST /documents`'s parent resource. Ownership scenarios are in section 9;
the 401 and cross-account cases live in `05_Security_Tests.md` section 7.

Contracts: `ProductSpecification/api-specs/documents_create.yaml`, `documents_get.yaml`,
`documents_save.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `document_type` `реферат`, `status` `draft`, `content` `""`, `version` `1` |
| Non-existent id | `00000000-0000-4000-8000-000000000000` |
| Idempotency key | `Idempotency-Key: 3f0c8a9e-2b41-4d77-9c6a-b5e1d2704f88` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| Content limit | 200 000 Unicode code points, measured NFC-normalized, before sanitization |

---

## 1. Create Document — Validation

### TC-05-API-1.1 — Reject unsupported document type

| Field | Value |
|---|---|
| Description | `document_type` is an enum of exactly four values. A fifth value must be refused before any row is written, or the catalogue silently grows types no downstream renderer understands. |
| Preconditions | Account A signed in; no document exists for account A. |
| Test data | Body `{"document_type": "статья"}` (outside `доклад`/`эссе`/`сочинение`/`реферат`), header `Idempotency-Key: 3f0c8a9e-2b41-4d77-9c6a-b5e1d2704f88` |
| Steps | 1. `POST /api/v1/documents` with account A's Bearer token, that header and that body.<br>2. `GET /api/v1/projects` (or list documents) for account A. |
| Expected result | `422 Unprocessable Entity`; body `{"error_code": "INVALID_DOCUMENT_TYPE", "message": "<generic text>"}`; step 2 shows no new document — the document count for account A is unchanged. |
| Status | Not run |

### TC-05-API-1.2 — Ignore server-owned fields in the request body

| Field | Value |
|---|---|
| Description | Mass assignment: a client that can set `status`, `id` or `content` at creation can forge a completed document or collide with an existing id. Per `decisions/server-owned-fields-ignored-decision.md` these are ignored, not rejected. |
| Preconditions | Account A signed in. |
| Test data | Body `{"document_type": "реферат", "status": "completed", "id": "11111111-1111-4111-8111-111111111111", "content": "<p>подделка</p>"}` |
| Steps | 1. `POST /api/v1/documents` with that body and a fresh `Idempotency-Key`.<br>2. Read `document_id` from the response and `GET /api/v1/documents/{document_id}`. |
| Expected result | `201 Created`; response `status` is `draft`, not `completed`; `document_id` is a server-generated UUID v4 different from `11111111-1111-4111-8111-111111111111`; `content` is `""`, not `<p>подделка</p>`; step 2 confirms the same three values as persisted. |
| Status | Not run |

---

## 2. Create Document — Happy Path

### TC-05-API-2.1 — Creating a manual document returns immediately with no linked generation

| Field | Value |
|---|---|
| Description | The manual path must be the AI path's opposite: one synchronous write, no queue, and above all no `Generation` row — a stray one would let story #1's completion path later mutate this document's status. |
| Preconditions | Account A signed in; the current `GET /api/v1/generations` count for account A is recorded. |
| Test data | Body `{"document_type": "реферат"}`, header `Idempotency-Key: 3f0c8a9e-2b41-4d77-9c6a-b5e1d2704f88` |
| Steps | 1. `POST /api/v1/documents` with that body and header.<br>2. Read the full response body and headers.<br>3. `GET /api/v1/generations` for account A and compare the count with the precondition. |
| Expected result | `201 Created` in a single synchronous response — no `202`, no `Location` to poll, no status-polling round trip; body carries `document_id` (UUID), `document_type` `реферат`, `status` `draft`, `content` `""`, an integer `version`, `created_at` and `updated_at` equal to each other; step 3's generation count is unchanged and no `Generation` row references the new `document_id`. |
| Status | Not run |

---

## 3. Create Document — Re-run Safety (idempotency)

### TC-05-API-3.1 — Replaying the same idempotency key does not create a duplicate document

| Field | Value |
|---|---|
| Description | A retried or double-clicked create must not leave the user with two empty documents. The replay is distinguished from the first call by its status code. |
| Preconditions | Account A signed in; `POST /api/v1/documents` has already been accepted once with `Idempotency-Key: key-1`, returning document A1. |
| Test data | Header `Idempotency-Key: key-1`; body `{"document_type": "реферат"}`, byte-identical to the first call |
| Steps | 1. Re-submit the identical `POST /api/v1/documents` with `Idempotency-Key: key-1`.<br>2. Compare the returned `document_id` with the first call's.<br>3. Count the documents owned by account A carrying that key. |
| Expected result | `200 OK`, not `201 Created`; the `document_id` is exactly `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` — the original document, not a new one; exactly one document exists for `key-1`. |
| Status | Not run |

---

## 4. Get Document

### TC-05-API-4.1 — Fetching a freshly created document returns its empty state

| Field | Value |
|---|---|
| Description | The editor opens on this response. An absent `version` here would leave the first save with no optimistic-concurrency token to send. |
| Preconditions | Document A1 has just been created by account A and never saved. |
| Test data | Document A1 id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` |
| Steps | 1. `GET /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` with account A's token. |
| Expected result | `200 OK`; `content` is exactly `""`; `version` is an integer (`1`); `status` is `draft`; `document_type` is `реферат`; `page_settings` is `null` (never configured), not a materialized default object. |
| Status | Not run |

### TC-05-API-4.2 — Requesting a non-existent document reports not found

| Field | Value |
|---|---|
| Description | The generic 404 is the same answer a foreign document gets (section 9.2), so this case pins the exact shape that the indistinguishability of the two depends on. |
| Preconditions | Account A signed in; no document exists with the id below. |
| Test data | `document_id = 00000000-0000-4000-8000-000000000000` |
| Steps | 1. `GET /api/v1/documents/00000000-0000-4000-8000-000000000000` with account A's token. |
| Expected result | `404 Not Found`; body exactly `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}`; the message contains no id and no internal detail. |
| Status | Not run |

---

## 5. Save Document — Validation

### TC-05-API-5.1 — Reject content exceeding the maximum length

| Field | Value |
|---|---|
| Description | Silent truncation is the failure this catches — the user would lose the tail of their own document without ever being told. |
| Preconditions | Document A1 exists at `version` `1` with `content` `""`. |
| Test data | `content` = the character `а` repeated 200 001 times; `version` = `1` |
| Steps | 1. `PUT /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` with `{"content": "<200 001 chars>", "version": 1}`.<br>2. `GET /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`. |
| Expected result | `400 Bad Request` with the `{"error_code", "message"}` shape; step 2 shows `content` still `""` and `version` still `1` — the oversized body is neither stored nor stored truncated to 200 000 characters. |
| Status | Not run |

### TC-05-API-5.2 — Accept content exactly at the maximum length, reject one character past it

| Field | Value |
|---|---|
| Description | Off-by-one at the boundary: a `>=` where `>` belongs rejects a legitimate 200 000-character document, and the reverse admits an unbounded one. |
| Preconditions | Document A1 exists at `version` `1`. |
| Test data | Content of exactly 200 000 characters, then of exactly 200 001 characters; `version` = the document's current value at each call |
| Steps | 1. `PUT /api/v1/documents/{A1}` with the 200 000-character content and `"version": 1`.<br>2. `PUT /api/v1/documents/{A1}` with the 200 001-character content and the version returned by step 1. |
| Expected result | Step 1 answers `200 OK` and the stored content is 200 000 characters long with the version advanced to `2`; step 2 answers `400 Bad Request` with the error shape and leaves `version` at `2`. |
| Status | Not run |

### TC-05-API-5.3 — Saving against a non-existent document reports not found

| Field | Value |
|---|---|
| Description | The save path must resolve the document before it validates anything else, so an unknown id cannot be probed through a different status code. |
| Preconditions | Account A signed in; no document exists with the id below. |
| Test data | `document_id = 00000000-0000-4000-8000-000000000000`, body `{"content": "<p>Текст</p>", "version": 1}` |
| Steps | 1. `PUT /api/v1/documents/00000000-0000-4000-8000-000000000000` with that body. |
| Expected result | `404 Not Found`; body exactly `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` — identical to TC-05-API-4.2's body. |
| Status | Not run |

### TC-05-API-5.4 — Ignore server-owned fields in the save request body

| Field | Value |
|---|---|
| Description | The save endpoint writes only `content` (and `title`); a client able to set `document_type`, `id` or `status` here could relabel or re-own a document through the editor. |
| Preconditions | Document A1 exists with `document_type` `реферат`, `status` `draft`, `version` `1`. |
| Test data | Body `{"content": "<p>Абзац</p>", "version": 1, "document_type": "эссе", "id": "11111111-1111-4111-8111-111111111111", "status": "completed"}` |
| Steps | 1. `PUT /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` with that body.<br>2. `GET /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`. |
| Expected result | `200 OK`; the saved `content` is `<p>Абзац</p>` and `version` is `2` — those two fields applied; `document_type` is still `реферат`, `status` is still `draft`, and the id is still `3d9b1f42-…` (the extra keys are ignored, per `decisions/server-owned-fields-ignored-decision.md`, not rejected with a `422`). |
| Status | Not run |

---

## 6. Save Document — Happy Path & Concurrency

### TC-05-API-6.1 — Saving persists the editor content and returns the updated state

| Field | Value |
|---|---|
| Description | The core round-trip: what the editor sent must come back on reopen, formatting included, with a version the next save can use. |
| Preconditions | Document A1 exists with `content` `""` and `version` `1`. |
| Test data | `content` = `<h2>Заголовок</h2><ul><li><b>Жирный</b> и <i>курсив</i></li></ul>`, `version` = `1` |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that content and `"version": 1`.<br>2. `GET /api/v1/documents/{A1}`. |
| Expected result | Step 1 answers `200 OK` with `version` `2` (the prior value plus exactly one) and `updated_at` later than `created_at`; step 2 returns the identical sanitized markup — the `<h2>`, `<ul><li>`, `<b>` and `<i>` elements all present and nested as sent. |
| Status | Not run |

### TC-05-API-6.2 — Saving the same content and version twice is idempotent

| Field | Value |
|---|---|
| Description | A retried autosave must not burn a version number, or the client's next legitimate save would see a spurious `409`. |
| Preconditions | Document A1 has just been saved with `<p>Абзац</p>`, leaving `version` `2`. |
| Test data | The exact same body as the accepted save: `{"content": "<p>Абзац</p>", "version": 1}` |
| Steps | 1. Re-submit the identical `PUT /api/v1/documents/{A1}` body.<br>2. `GET /api/v1/documents/{A1}`. |
| Expected result | `200 OK` (not `409`) reporting `content` `<p>Абзац</p>` and `version` `2`; step 2 confirms `version` is still `2` — no second write, no second version advance. |
| Status | Not run |

### TC-05-API-6.3 — A save against a stale version is rejected, never silently overwriting

| Field | Value |
|---|---|
| Description | The lost-update guard. Without it, a second editor tab silently discards the first tab's paragraph. |
| Preconditions | Document A1 was saved once with `<p>Первый</p>`, advancing `version` from `1` to `2`. |
| Test data | Second save body `{"content": "<p>Второй</p>", "version": 1}` — the original, now-stale version |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that stale-version body.<br>2. `GET /api/v1/documents/{A1}`. |
| Expected result | Step 1 answers `409 Conflict` with `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}`; step 2 shows `content` is still `<p>Первый</p>` and `version` still `2` — `<p>Второй</p>` was not written. |
| Status | Not run |

### TC-05-API-6.4 — An entirely Cyrillic, multi-paragraph document round-trips without corruption

| Field | Value |
|---|---|
| Description | Every character in this product's real content is multibyte. A byte-oriented truncation or a wrong column encoding shows up as mojibake or a dropped final character, not as an error. |
| Preconditions | Document A1 exists at a known version. |
| Test data | `content` = `<h2>Введение</h2><p>Первый абзац исследования.</p><p>Второй абзац.</p><ul><li>Пункт первый</li><li>Пункт второй</li></ul>` — no Latin characters in the text |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that content and the current version.<br>2. `GET /api/v1/documents/{A1}` and compare the returned `content` to the sent string. |
| Expected result | `200 OK`; the returned `content` equals the sent string character for character; no `?`, no `�`, no missing final character at any paragraph or element boundary. |
| Status | Not run |

### TC-05-API-6.5 — The max-length boundary never splits a multibyte character, including outside the BMP

| Field | Value |
|---|---|
| Description | Counting UTF-16 code units or bytes rather than code points lets the 200 000 cutoff land inside a surrogate pair, storing half an emoji. |
| Preconditions | Document A1 exists at a known version. |
| Test data | (a) Content engineered so the 200 000-code-point boundary lands mid-way through a 4-byte emoji (`🎓`, U+1F393) or a combining-accent sequence (`e` + U+0301). (b) Content composed entirely of `🎓`, exactly at the 200 000-code-point limit. |
| Steps | 1. `PUT /api/v1/documents/{A1}` with fixture (a) and the current version.<br>2. `PUT /api/v1/documents/{A1}` with fixture (b) and the then-current version.<br>3. `GET /api/v1/documents/{A1}` after step 2. |
| Expected result | The boundary is evaluated in whole code points on the NFC-normalized string: fixture (a) is accepted or rejected as a whole (`200` or `400`) but is never stored with a lone surrogate or a split combining sequence; fixture (b) answers `200 OK` and step 3 returns exactly 200 000 `🎓` characters, byte-identical to what was sent. |
| Status | Not run |

### TC-05-API-6.6 — Canonically-equivalent Unicode content is compared consistently for duplicate-save detection

| Field | Value |
|---|---|
| Description | If the duplicate-save comparison normalizes but the store does not (or the reverse), the same visible text can both advance and not advance the version depending on the client's keyboard. |
| Preconditions | Document A1 has just been saved with the NFC form of `Привет, Renée` at `version` `2`. |
| Test data | Resubmit the same visible text in NFD (`e` + U+0301 for `é`) with the same `version` value used by the accepted save |
| Steps | 1. `PUT /api/v1/documents/{A1}` with the NFD-encoded content and that version.<br>2. `GET /api/v1/documents/{A1}`. |
| Expected result | One of two consistent outcomes, the same on every run: either `200 OK` with `version` unchanged at `2` (recognized as the same content, no spurious advance), or `200 OK` with `version` `3` and the NFD form stored exactly as sent. In both cases step 2 returns text that renders as `Привет, Renée` with no corrupted or dropped combining mark. |
| Status | Not run |

### TC-05-API-6.7 — Same-instant concurrent saves against one document resolve atomically, exactly one wins

> **Fixture amended 2026-07-17 — the two requests must carry DISTINCT content.** As
> originally written this scenario was mutually unsatisfiable with 6.2. 6.2 requires an
> identical `(content, version)` resubmit to answer **200** with no version advance, which
> forces the save path to treat "the stored content already equals mine and the version
> advanced by exactly one" as a replay rather than a conflict. If 6.7's two concurrent
> requests carried *identical* content, the loser would match that very rule and get 200 —
> while 6.7 demands a conflict. Distinct content separates the two: the loser's content
> does not match what landed, so it is a genuine conflict. Without this the implementation
> must fail one scenario or the other, whichever is written second.

| Field | Value |
|---|---|
| Description | A read-modify-write that is not a single atomic compare-and-swap loses one of two same-instant saves without either client learning of it. |
| Preconditions | Document A1 exists at `version` `2`; two application instances share the same database, and the two requests can be latched at the read-modify-write window and released together (deterministic interleave, not a statistical race). |
| Test data | Request X: `{"content": "<p>Вариант X</p>", "version": 2}`; Request Y: `{"content": "<p>Вариант Y</p>", "version": 2}` — deliberately different content, same version |
| Steps | 1. Latch requests X and Y at the version compare-and-swap, routed to two different backend instances.<br>2. Release both at the same instant.<br>3. `GET /api/v1/documents/{A1}`. |
| Expected result | Exactly one of X and Y answers `200 OK` with `version` `3`; the other answers `409 Conflict` with `{"error_code": "VERSION_CONFLICT", …}`; step 3's `content` is exactly the winner's string — never interleaved, never partially applied, never a merge of both; `version` is `3`, not `4`. |
| Status | Not run |

---

## 8. Save Document — Version Field Validation

### TC-05-API-8.1 — A negative or non-integer version is rejected as invalid, not treated as a valid token

| Field | Value |
|---|---|
| Description | A lax `int` coerces `"5"`, `5.0` and JSON `true` into a valid-looking version, so a malformed token would silently pass the concurrency check. Distinct from 6.3, where the integer is well-formed but stale. |
| Preconditions | Document A1 exists at `version` `2`. |
| Test data | `version` values: `-1`, `"2"` (string), `2.5` (float), `true` (boolean), and `null` |
| Steps | 1. `PUT /api/v1/documents/{A1}` with `{"content": "<p>Текст</p>", "version": -1}`.<br>2. Repeat with each of `"2"`, `2.5`, `true`, `null` in the `version` field.<br>3. `GET /api/v1/documents/{A1}`. |
| Expected result | Every one of the five answers `422 Unprocessable Entity` with `{"error_code": "INVALID_VERSION", "message": "<generic text>"}` — never `200` and never `409`; step 3 shows `version` still `2` and the content unchanged. |
| Status | Not run |

---

## 7. Save Document — Content Safety

### TC-05-API-7.1 — Raw script/event-handler HTML submitted directly is neutralized, not stored verbatim

| Field | Value |
|---|---|
| Description | The editor's own formatting is not a security boundary — an attacker calls the API directly. Sanitization must happen server-side, before persist, on an allowlist. |
| Preconditions | Document A1 exists at a known version. |
| Test data | `content` = `<p>Текст</p><script>alert(1)</script><img src=x onerror=alert(1)>` sent directly in the `PUT` body, bypassing the editor UI |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that content and the current version.<br>2. `GET /api/v1/documents/{A1}` and inspect the raw `content` string. |
| Expected result | `200 OK`; neither the save response nor the read contains the substring `<script`, the substring `onerror`, or any executable markup — the `<script>` element is stripped and the `onerror` attribute removed; the allowed `<p>Текст</p>` survives intact. |
| Status | Not run |

### TC-05-API-7.2 — When sanitization alters submitted content, the response reflects what was actually stored

| Field | Value |
|---|---|
| Description | Echoing the submitted content back would leave the client's editor showing markup that is not in the database — the divergence surfaces only on the next reload. |
| Preconditions | Document A1 exists at a known version. |
| Test data | `content` = `<p>Начало</p><div onclick="steal()">Блок</div>` — the `<div>`/`onclick` is stripped by the allowlist |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that content and the current version; record the response `content`.<br>2. `GET /api/v1/documents/{A1}`; record its `content`.<br>3. Compare both against the submitted string. |
| Expected result | `200 OK`; the step-1 and step-2 `content` values are identical to each other and both carry no `onclick` attribute; neither is byte-identical to the submitted string — the response is the sanitized, persisted form, not an echo. |
| Status | Not run |

---

## 9. Document Ownership

> Added 2026-07-17 — see `decisions/document-ownership-decision.md`. The cross-account and
> missing-token cases live in `05_Security_Tests.md` section 7; these are the owner-scoping
> rules the happy paths depend on.

### TC-05-API-9.1 — A created document belongs to the authenticated account

| Field | Value |
|---|---|
| Description | The owner must come from the verified token, never from a client-supplied field — otherwise a caller could create a document straight into another account. |
| Preconditions | Accounts A and B both exist; account A is signed in. |
| Test data | Body `{"document_type": "реферат", "owner_id": "<account B's user id>"}`, header `Idempotency-Key: <fresh UUID>` |
| Steps | 1. `POST /api/v1/documents` as account A with that body.<br>2. `GET /api/v1/documents/{document_id}` as account A.<br>3. `GET /api/v1/documents/{document_id}` as account B. |
| Expected result | Step 1 answers `201 Created`; step 2 answers `200 OK` — the document is account A's; step 3 answers `404 Not Found` with `{"error_code": "NOT_FOUND", …}` — the `owner_id` in the body was ignored and ownership was taken from account A's access token. |
| Status | Not run |

### TC-05-API-9.2 — A fetch returns only the authenticated account's own document

| Field | Value |
|---|---|
| Description | A `403` for a foreign id would confirm that the id exists, turning the endpoint into an existence oracle. The refusal must be the same `404` an unknown id gets. |
| Preconditions | Document A1 exists and is owned by account A; account B exists and is signed in. |
| Test data | Document A1 id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`; non-existent id `00000000-0000-4000-8000-000000000000` |
| Steps | 1. `GET /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` with account A's token.<br>2. Repeat with account B's token.<br>3. `GET /api/v1/documents/00000000-0000-4000-8000-000000000000` with account B's token and compare with step 2. |
| Expected result | Step 1 answers `200 OK` with document A1's body; step 2 answers `404 Not Found`, never `403`; the status line and body of steps 2 and 3 are identical — `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` in both. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `a document type other than the 4 supported values` | `document_type: "статья"` (or any value outside доклад/эссе/сочинение/реферат) |
| `sets a status, an id, and non-empty content` | request body includes `status: "completed"`, `id: "<attacker-uuid>"`, `content: "<attacker-text>"` on `POST /api/v1/documents` |
| `the response confirms the document was created` | `201 Created` with `document_id`, `status: "draft"`, `content: ""`, `version` in body |
| `no generation record is created or linked` | no `Generation` row exists referencing the new `document_id`; `GET /generations` count unchanged |
| `idempotency key "key-1"` | `Idempotency-Key: key-1` request header on `POST /api/v1/documents` |
| `the response refers to the original document` | `200 OK` (not `201`) with the same `document_id` as the first call |
| `fetches it` / `fetches that id` | `GET /api/v1/documents/{document_id}` |
| `a version token` | `version` integer field in the response |
| `no document exists with a given id` | random UUID never used as a `document_id` |
| `exceeds the maximum allowed length` | `content` longer than 200,000 characters |
| `exactly at the maximum allowed length` / `one character past it` | `content` length exactly 200,000 / 200,001 characters |
| `submits a save request for that id` | `PUT /api/v1/documents/{document_id}` |
| `sets a document_type, an id, and a status` | `PUT` body includes `document_type: "эссе"`, `id: "<attacker-uuid>"`, `status: "completed"` alongside `content`/`version` |
| `formatted content (headings, a list, bold, italic)` | sanitized HTML fixture using `<h1>`/`<h2>`, `<ul><li>`, `<b>`, `<i>` |
| `the document's version has advanced` | response `version` is the prior value + 1 |
| `the same save request again` | identical `content` and `version` resubmitted on the second `PUT` |
| `a version conflict` | `409 Conflict` response |
| `entirely Cyrillic, multi-paragraph` | fixture text with no Latin characters, spanning multiple `<h2>`/`<p>`/`<li>` elements |
| `raw script tags and event-handler attributes` | `<script>alert(1)</script>`, `<img onerror=alert(1)>` sent directly in the `PUT` body's `content` field, bypassing the editor UI |
| `sanitized` | server-side allowlist-based HTML sanitizer strips disallowed tags/attributes before persist |
| `disallowed tags or attributes that get stripped` | e.g. `<div onclick=...>` inside otherwise-valid formatted content |
| `the 200,000-character boundary lands in the middle of a multi-code-unit character` | fixture engineered so a surrogate-pair emoji or combining-accent sequence straddles the exact `content` length cutoff |
| `outside the Basic Multilingual Plane` | e.g. 4-byte-UTF-8 emoji codepoints, distinct from the existing Cyrillic (BMP) fixture in 6.4 |
| `a different Unicode normalization form (NFC vs. NFD)` | same visible text encoded as precomposed (NFC) vs. decomposed (NFD) combining-character sequences |
| `released to execute at the same instant` | two save requests latched at the read-modify-write window and released together (deterministic interleave, not a statistical race), or a storage-adapter-level test asserting the version compare-and-swap is a single atomic statement |
| `different backend instances` | the two concurrent saves are routed to two separate application instances sharing the same database |
| `version -1` / `a non-integer version value` | malformed `version` field in the `PUT` body, distinct from the valid-but-stale integer already covered in 6.3 |
