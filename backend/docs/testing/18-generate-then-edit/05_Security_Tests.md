<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Generate → edit — Security Tests

Stack-aware scenarios for the conversion endpoint. Generic auth (401), headers, CORS, and
HTTPS are covered globally and omitted here.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Account B (a stranger) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Generation G1 (completed, owned by A) | id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426`, topic `История Москвы` |
| Generation G2 (completed, owned by B) | id `a91c6b34-2d70-4f85-9c1e-6b04a7f2d539` |
| Absent id | `00000000-0000-4000-8000-000000000000` |
| Conversion request | `POST /api/v1/documents/from-generation`, body `{"generation_id": "<uuid>"}`, header `Idempotency-Key` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| Not-found body | `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}` |
| Internal-error body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |

---

## 1. Authorization / IDOR

### TC-18-SEC-1.1 — A foreign generation cannot be converted, and existence is not disclosed

| Field | Value |
|---|---|
| Description | A `403` on a foreign generation confirms the id exists, turning the endpoint into an oracle over other users' work — and converting one would copy their text into the attacker's account. |
| Preconditions | Generation G2 exists, completed, owned by account B; account A signed in; no generation exists under the absent id. |
| Test data | G2's id and the absent id, each with a fresh `Idempotency-Key` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G2 with account A's token.<br>2. Repeat with the absent id.<br>3. Compare the two responses byte for byte and compare their response times.<br>4. Count documents for accounts A and B. |
| Expected result | Both answer `404 Not Found`, never `403`; both bodies are the not-found body above; status line and headers (bar `Date`) are identical and the timing difference does not distinguish them; no document is created for either account and G2 stays unconverted. |
| Status | Not run |

### TC-18-SEC-1.2 — A generated document is not readable or editable by another account

| Field | Value |
|---|---|
| Description | Ownership is re-asserted on the created document, not only on the generation: a document minted by the conversion path must be as private as one created by hand. |
| Preconditions | Account A has converted G1 into a document; the `document_id` is recorded; account B is signed in. |
| Test data | The converted `document_id`; a truly non-existent document id `00000000-0000-4000-8000-000000000000`; a `PUT` body `{"content": "<p>Чужая правка.</p>", "version": 1}` |
| Steps | 1. `GET /api/v1/documents/{document_id}` with account B's token.<br>2. `PUT /api/v1/documents/{document_id}` with account B's token and the body above.<br>3. `GET /api/v1/documents/00000000-0000-4000-8000-000000000000` with account B's token and compare with step 1 byte for byte.<br>4. `GET /api/v1/documents/{document_id}` with account A's token. |
| Expected result | Steps 1 and 2 answer `404` with the not-found body, never `403` and never `200`; step 3's response is byte-identical to step 1's (bar `Date`); step 4 shows account A's content unchanged — `Чужая правка.` was never stored. |
| Status | Not run |

---

## 2. Mass Assignment

### TC-18-SEC-2.1 — Server-owned fields on the conversion body cannot be set

| Field | Value |
|---|---|
| Description | If the body's fields are bound onto the entity, a caller can mint a document at an arbitrary version or status — or attach it to a generation belonging to someone else. |
| Preconditions | Generation G1 completed and owned by account A; generation G2 owned by account B. |
| Test data | Body `{"generation_id": "4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426", "title": "Взломанный заголовок", "id": "11111111-1111-4111-8111-111111111111", "status": "published", "version": 99}`; a second attempt substituting G2's id |
| Steps | 1. `POST /api/v1/documents/from-generation` with the body above using account A's token.<br>2. Read the response and the stored row field by field.<br>3. Repeat with `"generation_id": "a91c6b34-2d70-4f85-9c1e-6b04a7f2d539"` (account B's generation). |
| Expected result | Step 1 answers `201` with a server-minted `document_id` (not `1111…`), a server-derived `title` (not `Взломанный заголовок`), `status` `draft` (not `published`), `version` `1` (not `99`) and `generation_id` = G1's id; step 3 answers `404` and creates nothing. |
| Status | Not run |

---

## 3. Output Encoding / XSS

### TC-18-SEC-3.1 — Model markup and dangerous URL schemes are neutralized

| Field | Value |
|---|---|
| Description | Model output is untrusted input that lands in the editor and in every later export — this is the product's primary stored-XSS path, and stripping only `<script>` leaves the `href`/`src` sinks open. |
| Preconditions | Generation G14 completed, owned by account A, with the hostile content below. |
| Test data | Generation G14 id `af02d597-3c6b-4718-9204-6e8b1d3a5c72`; content `<script>alert(1)</script> <div onclick="alert(2)">блок</div> [клик](javascript:alert(3)) [док](data:text/html;base64,PHNjcmlwdD5hbGVydCg0KTwvc2NyaXB0Pg==) <img src=x onerror="alert(5)">` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G14.<br>2. Inspect the `content` in the response.<br>3. `GET /api/v1/documents/{document_id}` and inspect the stored content.<br>4. Open the document in the editor and watch for dialogs. |
| Expected result | `201`; neither the response nor the stored content contains `<script`, `onclick=`, `onerror=`, `alert(`, an `href` starting `javascript:`, or a `src`/`href` starting `data:`; the visible text `блок`, `клик` and `док` survives; no dialog fires when the document renders. |
| Status | Not run |

---

## 4. Fail-Closed

### TC-18-SEC-4.1 — A sanitizer or parser failure stores nothing unsanitized

| Field | Value |
|---|---|
| Description | A conversion that falls back to the raw text when sanitization fails persists exactly the payload the sanitizer exists to remove — a failure that is invisible until it is exploited. |
| Preconditions | Generation G12 completed, owned by account A; the sanitizer (and separately the parser) can be made to raise. |
| Test data | Generation G12 id `3f7e0a92-5b46-4c18-9d70-2c8b6a1f4e53`; source carrying the marker `UNSANITIZED-MARKER` and a `<script>` tag; injected sanitizer failure, then injected parser failure |
| Steps | 1. `POST /api/v1/documents/from-generation` for G12 with the sanitizer made to raise.<br>2. Repeat with the parser made to raise.<br>3. Count documents for account A after each.<br>4. Search the whole documents table for `UNSANITIZED-MARKER` and for `<script`. |
| Expected result | Both attempts fail with a non-`2xx` — `500` with the internal-error body — and neither creates a document; `UNSANITIZED-MARKER` and `<script` appear nowhere in storage; a later retry after the injection is removed converts normally. |
| Status | Not run |

---

## 5. Disclosure

### TC-18-SEC-5.1 — Error paths leak no internal detail

| Field | Value |
|---|---|
| Description | A database message names the schema, an id shape names the identifier scheme, a stack frame names the file layout — in a body or in a log line, each hands an attacker a map. |
| Preconditions | Each failure family — not-found, not-completed, content-too-long, parser/sanitizer failure, storage failure — can be triggered with a seeded sentinel. |
| Test data | Sentinels `relation "documents" does not exist`, `generation 4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426 not found`, `File "/app/usecase/src/document/create_document_from_generation.py", line 68` |
| Steps | 1. Trigger each failure family with its sentinel seeded.<br>2. Read each response body in full.<br>3. Read the client-level application log lines emitted for each. |
| Expected result | Every body matches `{"error_code": "<CODE>", "message": "<fixed generic text>"}` with a code from the sanctioned set (`NOT_FOUND`, `GENERATION_NOT_COMPLETED`, `CONVERTED_CONTENT_TOO_LONG`, `INVALID_IDEMPOTENCY_KEY`, `INTERNAL_ERROR`); no sentinel — raw, encoded or partially quoted — appears in any response body or client-level log line. |
| Status | Not run |
