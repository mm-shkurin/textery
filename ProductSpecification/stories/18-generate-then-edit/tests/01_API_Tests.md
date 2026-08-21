> **Implementation Order**: sequential TDD — prerequisite guards → idempotent+race-safe
> conversion → validation → output safety.

# Generate → edit — API Tests

Endpoint: `POST /api/v1/documents/from-generation`. Reused endpoints covered by stories 1 and 5.
Contract: `ProductSpecification/api-specs/documents_from_generation.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Generation G1 (completed, owned by A) | id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426`, `document_type` `доклад`, topic `История Москвы`, content `## Введение\n\nПервый абзац.` |
| Generation G2 (completed, owned by B) | id `a91c6b34-2d70-4f85-9c1e-6b04a7f2d539` |
| Absent generation id | `00000000-0000-4000-8000-000000000000` |
| Idempotency key | `Idempotency-Key: 6f3b91d2-4a58-4c7e-8d10-2e9f5b7a63c4` (1–128 chars, required) |
| Request body | `{"generation_id": "<uuid>"}` |
| Success body | `DocumentResponse` — `document_id`, `document_type`, `generation_id`, `title`, `status` (`draft`), `content` (sanitized HTML), `version`, `created_at`, `updated_at` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| Content limit | `200000` Unicode code points |

## 1. Prerequisite Guards

### TC-18-API-1.1 — Conversion of a non-existent generation is refused

| Field | Value |
|---|---|
| Description | An unknown generation must be refused before any parse or insert; a `500` here would turn a typo'd id into an internal error and a partial write. |
| Preconditions | Account A signed in; no generation exists under the absent id; the documents table row count is recorded. |
| Test data | `{"generation_id": "00000000-0000-4000-8000-000000000000"}`, a fresh `Idempotency-Key` |
| Steps | 1. `POST /api/v1/documents/from-generation` with that body and key, using account A's token.<br>2. Re-count account A's documents. |
| Expected result | `404 Not Found`; body `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}`; the document count is unchanged. |
| Status | Not run |

### TC-18-API-1.2 — Conversion of another account's generation is refused indistinguishably

| Field | Value |
|---|---|
| Description | A `403` would confirm the generation exists, making the endpoint an id oracle over other people's work. |
| Preconditions | Generation G2 exists, completed, owned by account B; account A signed in. |
| Test data | `{"generation_id": "a91c6b34-2d70-4f85-9c1e-6b04a7f2d539"}`, a fresh `Idempotency-Key` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G2 with account A's token.<br>2. Repeat TC-18-API-1.1 and compare the two responses byte for byte.<br>3. Count documents for both accounts. |
| Expected result | `404 Not Found`, never `403`; status line, headers (bar `Date`) and body identical to the absent-id response; no document is created for either account. |
| Status | Not run |

### TC-18-API-1.3 — Conversion of a not-completed generation is refused (each non-terminal state)

| Field | Value |
|---|---|
| Description | Converting a half-written generation hands the user a truncated document as if it were finished. Each non-completed state must be refused on its own, not merely the one the fixture happens to produce. |
| Preconditions | Three generations owned by account A, one in each state below; no document exists for any of them. |
| Test data | `pending` → id `b3e7d248-5a91-4c60-9f82-7d1e4a06c5b8`; `in_progress` → id `c58a1f60-9d24-4b73-8e05-3a7c6b2f4d91`; `failed` → id `d70b4c93-1e85-4a26-b9d3-8f52a1c07e64` |
| Steps | 1. `POST /api/v1/documents/from-generation` for the `pending` generation.<br>2. Repeat for `in_progress`.<br>3. Repeat for `failed`.<br>4. Count documents for account A after each. |
| Expected result | Each of the three answers `409 Conflict` with `{"error_code": "GENERATION_NOT_COMPLETED", "message": "This generation is not finished yet and cannot become a document."}` — not `VERSION_CONFLICT`; no document is created in any of the three. |
| Status | Not run |

### TC-18-API-1.4 — Conversion of a generation in an unknown status fails closed

| Field | Value |
|---|---|
| Description | The status set grows; an allowlist refuses the status nobody remembered to handle, a denylist converts it. |
| Preconditions | Generation G3 owned by account A whose stored status is a value the code does not recognise, written directly to storage. |
| Test data | Generation G3 id `e2c9047b-6835-4d1a-a7f0-95b3e8d1c206`, `status = archived_v2` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G3.<br>2. Count documents for account A.<br>3. Check whether the markdown converter or sanitizer was invoked. |
| Expected result | `409 Conflict` with `{"error_code": "GENERATION_NOT_COMPLETED", …}`; no document is created; conversion is never attempted — neither the parser nor the sanitizer runs. |
| Status | Not run |

## 2. Convert — Happy Path

### TC-18-API-2.1 — A completed generation converts to an editable document

| Field | Value |
|---|---|
| Description | The whole auto-open flow rests on this: until the text is a Document it has no id to save against and no version to guard a save with. |
| Preconditions | Generation G1 exists, completed, owned by account A, not yet converted. |
| Test data | `{"generation_id": "4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426"}`, `Idempotency-Key: 6f3b91d2-4a58-4c7e-8d10-2e9f5b7a63c4` |
| Steps | 1. `POST /api/v1/documents/from-generation` with that body and key.<br>2. Read the response body.<br>3. Read the generation row for G1. |
| Expected result | `201 Created`; body carries `generation_id` = G1's id, `version` = `1`, `status` = `draft`, `document_type` = `доклад`, a non-empty server-derived `title` (from the topic `История Москвы`), and `content` as sanitized HTML (`<h2>Введение</h2><p>Первый абзац.</p>`); the generation row is unchanged. |
| Status | Not run |

### TC-18-API-2.2 — The converted document is retrievable and editable

| Field | Value |
|---|---|
| Description | A converted document must be an ordinary document — if the read or save path treats it specially, the editor breaks on exactly the documents users actually have. |
| Preconditions | Generation G1 has been converted; the resulting `document_id` and `version` are recorded. |
| Test data | The `document_id` from TC-18-API-2.1, `version` `1`, new content `<p>Отредактированный абзац.</p>` |
| Steps | 1. `GET /api/v1/documents/{document_id}` with account A's token.<br>2. `PUT /api/v1/documents/{document_id}` with the new content and `version` `1`.<br>3. `GET /api/v1/documents/{document_id}` again. |
| Expected result | Step 1 answers `200` with the converted content; step 2 answers `2xx` and returns `version` `2`; step 3 shows `<p>Отредактированный абзац.</p>` and `version` `2`; `generation_id` is still G1's id after the edit. |
| Status | Not run |

## 3. Idempotency & Race Safety

### TC-18-API-3.1 — Replaying the same idempotency key returns the same document

| Field | Value |
|---|---|
| Description | A retried request — from a flaky network or a StrictMode double-invoke — must not mint a second document holding half the user's edits. |
| Preconditions | Generation G1 already converted with the key below; the resulting `document_id` recorded. |
| Test data | Same body and same `Idempotency-Key: 6f3b91d2-4a58-4c7e-8d10-2e9f5b7a63c4` |
| Steps | 1. Re-send the identical `POST /api/v1/documents/from-generation`.<br>2. Compare the returned `document_id` with the recorded one.<br>3. Count documents for account A. |
| Expected result | `200 OK` (not `201`); the body is the existing document with the same `document_id` and `version`; account A's document count is unchanged — no second row. |
| Status | Not run |

### TC-18-API-3.2 — A repeat conversion for the same generation returns the same document

| Field | Value |
|---|---|
| Description | Idempotency keyed only on the header would let a new key duplicate one generation into two documents; the unique constraint on `generation_id` is what actually closes it. |
| Preconditions | Generation G1 already converted; the resulting `document_id` recorded. |
| Test data | Same `generation_id`, a **new** `Idempotency-Key: 8a1d4c67-3b29-4e50-91f6-0c7d2b8e5a13` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G1 with the new key.<br>2. Compare the returned `document_id` with the recorded one.<br>3. Count documents linked to G1. |
| Expected result | `200 OK` returning the existing document with the same `document_id`; exactly one document row carries `generation_id` = G1's id. |
| Status | Not run |

### TC-18-API-3.3 — Two concurrent conversions of one generation yield exactly one document

| Field | Value |
|---|---|
| Description | The client can fire twice from two poll observations, and two instances can both pass the existence check before either inserts. A check-then-insert without a database constraint duplicates here. |
| Preconditions | Generation G4 completed, owned by account A, not yet converted; both requests held at a barrier placed between the existence check and the insert (ideally on two instances). |
| Test data | Generation G4 id `f16e83a2-40c7-4b95-8d3e-2a9f7c604b18`; two distinct idempotency keys; barrier released simultaneously |
| Steps | 1. Issue both conversion requests and hold them at the barrier.<br>2. Release both together.<br>3. Read both responses.<br>4. Count document rows with `generation_id` = G4's id. |
| Expected result | Exactly one row exists for G4; one response is `201` and the other `200`, both carrying the same `document_id`; the loser is never an error — no `409`, no `500`. |
| Status | Not run |

### TC-18-API-3.4 — A failure mid-conversion leaves no partial state

| Field | Value |
|---|---|
| Description | An orphan document row or a stranded idempotency marker permanently blocks the retry, leaving the user with a generation that can never become a document. |
| Preconditions | Generation G5 completed, owned by account A, not converted; the write is made to fail after the insert is prepared and before the commit. |
| Test data | Generation G5 id `0b7f52e9-8c14-4a63-9e27-5d3a1f06c8b4`; injected failure at the conversion write; a fresh key for the retry |
| Steps | 1. `POST /api/v1/documents/from-generation` for G5 with the failure injected.<br>2. Query the documents table for `generation_id` = G5's id and for any idempotency marker for that key.<br>3. Remove the injected failure and retry with a fresh key. |
| Expected result | Step 1 answers `500` with `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; step 2 finds zero document rows and no idempotency marker for G5; step 3 answers `201` and creates the document normally. |
| Status | Not run |

### TC-18-API-3.5 — A stale save of a generated document is rejected

| Field | Value |
|---|---|
| Description | Two tabs opened on the auto-converted document is the ordinary case here; without the version guard the second save silently erases the first. |
| Preconditions | Generation G1 converted into a document; two sessions hold that document at `version` `1`. |
| Test data | `document_id` from TC-18-API-2.1; session 1 saves `<p>Правка первой сессии.</p>` at `version` `1`; session 2 then saves `<p>Правка второй сессии.</p>` at `version` `1` |
| Steps | 1. Session 1 `PUT /api/v1/documents/{document_id}` with `version` `1`.<br>2. Session 2 `PUT /api/v1/documents/{document_id}` with the stale `version` `1`.<br>3. `GET /api/v1/documents/{document_id}`. |
| Expected result | Step 1 answers `2xx` with `version` `2`; step 2 answers `409 Conflict` with `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}`; step 3 shows `Правка первой сессии.` — session 1's edit was not overwritten. |
| Status | Not run |

### TC-18-API-3.6 — Pathological markdown converts within a bounded time

| Field | Value |
|---|---|
| Description | Markdown parsing on untrusted model text can be super-linear; a deeply nested document under the size limit is then a one-request denial of service. |
| Preconditions | Generation G6 completed, owned by account A, whose content is deeply nested markdown but under the content limit. |
| Test data | Generation G6 id `7c3d9a15-6e82-4f47-b05c-1a4e8b2d3f69`; content = 5000 levels of nested list/emphasis, total length < 200000 code points; wall-clock bound `5 s` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G6 and time the call.<br>2. After it returns, issue a normal conversion for a fresh completed generation.<br>3. Check the worker pool for stuck workers. |
| Expected result | The call returns within `5 s` — either `201` with sanitized content, or a `4xx` refusing it on nesting depth; step 2 answers promptly, proving no worker hangs; no request is left in flight after the call returns. |
| Status | Not run |

## 4. Validation

### TC-18-API-4.1 — Server-owned fields in the body are ignored

| Field | Value |
|---|---|
| Description | Mass assignment here would let a caller mint a document at an arbitrary version or attach it to a generation they do not own. |
| Preconditions | Generation G1 completed and owned by account A; generation G2 owned by account B. |
| Test data | Body `{"generation_id": "4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426", "title": "Взломанный заголовок", "id": "11111111-1111-4111-8111-111111111111", "status": "published", "version": 99}` plus a second attempt whose `generation_id` is G2's id |
| Steps | 1. `POST /api/v1/documents/from-generation` with the body above.<br>2. Read the response body and the stored row.<br>3. Repeat with G2's id in the body and account A's token. |
| Expected result | Step 1 answers `201` with `generation_id` = G1's id, a server-derived `title` (not `Взломанный заголовок`), a server-minted `document_id` (not the submitted `id`), `status` = `draft` (not `published`) and `version` = `1` (not `99`); step 3 answers `404` and creates nothing. |
| Status | Not run |

### TC-18-API-4.2 — A manual document creation rejects a client-supplied generation link

| Field | Value |
|---|---|
| Description | If the manual create accepted a `generation_id`, a caller could attach a blank document to someone else's generation and defeat the unique-constraint guard from the other side. |
| Preconditions | Account A signed in; generation G1 exists. |
| Test data | `POST /api/v1/documents` with body `{"document_type": "доклад", "generation_id": "4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426"}`, a fresh `Idempotency-Key` |
| Steps | 1. `POST /api/v1/documents` with that body.<br>2. Read the response and the stored row. |
| Expected result | The created document's `generation_id` is `null` — the submitted value is rejected, never stored; the document is not linked to G1 and G1 remains convertible. |
| Status | Not run |

### TC-18-API-4.3 — Converted content over the limit is rejected at the boundary

| Field | Value |
|---|---|
| Description | Truncating instead of refusing silently loses the tail of the user's document, and a byte-based cut can split a grapheme mid-character. |
| Preconditions | Generation G7 completed, owned by account A, whose converted HTML exceeds the limit by a two-code-point grapheme straddling the boundary. |
| Test data | Generation G7 id `5e0b7d34-9a61-4c28-8f75-3b6d2c9e1047`; limit `200000` Unicode code points; converted length `200001` code points, the last grapheme being `e` + U+0301 |
| Steps | 1. `POST /api/v1/documents/from-generation` for G7.<br>2. Count documents for account A.<br>3. Inspect the response body. |
| Expected result | `422 Unprocessable Entity` with `{"error_code": "CONVERTED_CONTENT_TOO_LONG", "message": "The generated text exceeds the maximum length of 200000 characters."}`; no document is created; nothing is truncated — no partially stored content exists anywhere. |
| Status | Not run |

### TC-18-API-4.4 — Source content is bounded before the parser runs

| Field | Value |
|---|---|
| Description | Capping only the converted output means the parser has already run on the oversized input — which is exactly the expensive step the cap was meant to prevent. |
| Preconditions | Generation G8 completed, owned by account A, whose **source** content is far past any sane bound; the markdown converter is instrumented to record invocation. |
| Test data | Generation G8 id `9f4a1c58-2073-4b6e-a91d-8c5e0b3f7d26`; source content `5 000 000` code points |
| Steps | 1. `POST /api/v1/documents/from-generation` for G8 and time the call.<br>2. Read whether the markdown converter and sanitizer were invoked.<br>3. Count documents for account A. |
| Expected result | A `422` is returned quickly (well under the pathological-render bound of `5 s`); the converter and sanitizer were never invoked on the full source; no document is created. |
| Status | Not run |

## 5. Content Fidelity & Output Safety

### TC-18-API-5.1 — Multibyte content round-trips byte-exact

| Field | Value |
|---|---|
| Description | An encoding slip anywhere along parse → sanitize → store → read turns the user's text into mojibake, and only a byte-exact comparison catches a single mangled character. |
| Preconditions | Generation G9 completed, owned by account A, with the multibyte content below. |
| Test data | Generation G9 id `2a8c6f01-b374-4e59-9d82-6f1a3c7e05b4`; content `Привет 🎓 é (e + U+0301) — тире` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G9.<br>2. `GET /api/v1/documents/{document_id}` for the created document.<br>3. Compare the read content with the source after NFC normalization, byte for byte. |
| Expected result | `201`, then `200`; the read text is byte-identical to the source after NFC normalization; `Привет`, the graduation-cap emoji, the accented `é` and the em dash all survive; no `?` and no `�` appear. |
| Status | Not run |

### TC-18-API-5.2 — Script and event-handler markup is neutralized

| Field | Value |
|---|---|
| Description | Markdown permits raw embedded HTML by design, so a `<script>` in the model's answer reaches storage unless the sanitizer runs after the parser — this is the stored-XSS path. |
| Preconditions | Generation G10 completed, owned by account A, with the hostile content below. |
| Test data | Generation G10 id `6d1b9e47-0c85-4a32-b7f6-9e2d4a8c3510`; content `Текст <script>alert(1)</script> и <div onclick="alert(2)">блок</div> и <img src=x onerror="alert(3)">` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G10.<br>2. Read the `content` in the response body.<br>3. `GET /api/v1/documents/{document_id}` and read the stored content.<br>4. Render the document in the editor. |
| Expected result | `201`; neither the response body nor the stored content contains `<script`, `onclick=`, `onerror=` or the string `alert(`; the surrounding text `Текст` and `блок` is preserved; no dialog fires when the document is rendered. |
| Status | Not run |

### TC-18-API-5.3 — Dangerous URL schemes are neutralized

| Field | Value |
|---|---|
| Description | Stripping only `<script>` leaves the link and image sinks open — `javascript:` and `data:` URIs execute from an `href` or a `src` just as well. |
| Preconditions | Generation G11 completed, owned by account A, with the content below. |
| Test data | Generation G11 id `8b5c2d70-4f19-4e83-a06b-1d7e9c4a2f35`; content ``[клик](javascript:alert(1)) [док](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==) <img src="x" onerror="alert(1)">`` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G11.<br>2. Read the emitted `content` and inspect every `href` and `src`.<br>3. `GET` the stored document and repeat the inspection. |
| Expected result | `201`; no `href` or `src` in the emitted or stored content begins with `javascript:` or `data:` — they are removed or replaced with a safe value; `onerror` is gone; the visible link text `клик` and `док` is preserved. |
| Status | Not run |

### TC-18-API-5.4 — A sanitizer or parser failure fails closed

| Field | Value |
|---|---|
| Description | A conversion that fails open stores unsanitized model output — the exact string the sanitizer exists to remove, persisted and served to the editor. |
| Preconditions | Generation G12 completed, owned by account A, whose content makes the parser or sanitizer raise; the sanitizer's failure is injectable. |
| Test data | Generation G12 id `3f7e0a92-5b46-4c18-9d70-2c8b6a1f4e53`; injected sanitizer exception; a marker string `UNSANITIZED-MARKER` present in the source |
| Steps | 1. `POST /api/v1/documents/from-generation` for G12.<br>2. Count documents for account A.<br>3. Search the documents table for `UNSANITIZED-MARKER`. |
| Expected result | The request fails with `500` and `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; no document is created; `UNSANITIZED-MARKER` appears nowhere in storage. |
| Status | Not run |

### TC-18-API-5.6 — Markup and schemes are stripped regardless of case, under a hostile locale

| Field | Value |
|---|---|
| Description | A case-insensitive match implemented with locale-sensitive lowercasing fails under a Turkish-style locale, where `I` does not fold to `i` — and `JAVASCRIPT:` then survives. |
| Preconditions | Generation G13 completed, owned by account A; the server process runs under a locale whose case-folding differs from the default. |
| Test data | Generation G13 id `1c6a4b28-7d93-4f50-8e21-5b0d3c9f6a74`; content `<SCRIPT>alert(1)</SCRIPT> [x](JavaScript:alert(2)) <IMG SRC=y ONERROR="alert(3)">`; locale `tr_TR.UTF-8` |
| Steps | 1. Start the backend with `LANG=tr_TR.UTF-8`.<br>2. `POST /api/v1/documents/from-generation` for G13.<br>3. Inspect the emitted and stored content case-insensitively for `script`, `javascript:` and `onerror`. |
| Expected result | `201`; no form of `<script`, `javascript:` or `onerror` — in any letter case — survives into the emitted or stored content; the result is identical to the same fixture converted under the default locale. |
| Status | Not run |

### TC-18-API-5.5 — Error bodies expose no internal detail

| Field | Value |
|---|---|
| Description | A database message, an internal id shape or a stack frame in an error body names the stack and the schema; a log that echoes it leaks the same to anyone with log access. |
| Preconditions | Each failure family — not-found, not-completed, content-too-long, parser failure, storage failure — can be triggered with a seeded sentinel. |
| Test data | Sentinels `relation "documents" does not exist`, `generation 4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426 not found`, `File "/app/usecase/src/document/create_document_from_generation.py", line 68`; fixed redaction token |
| Steps | 1. Trigger each failure family with its sentinel seeded, including the parser-failure family.<br>2. Read each response body in full.<br>3. Read the client-level application log lines emitted for each. |
| Expected result | Every body matches `{"error_code": "<CODE>", "message": "<fixed generic text>"}` with `<CODE>` one of `NOT_FOUND`, `GENERATION_NOT_COMPLETED`, `CONVERTED_CONTENT_TOO_LONG`, `INVALID_IDEMPOTENCY_KEY`, `INTERNAL_ERROR`; no sentinel — raw, encoded or partially quoted — appears in any body or client-level log line; internal detail is replaced by the fixed redaction token rather than re-encoded. |
| Status | Not run |
