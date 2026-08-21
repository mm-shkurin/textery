<!-- COPIED FILE. Source of truth: ProductSpecification/stories/05-manual-mode/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Manual input mode (non-AI document creation) — Security Tests

Scope note **rewritten 2026-07-17** — see `decisions/document-ownership-decision.md`.
The original read: *"this story is fully anonymous (no auth, no JWT, no session/CSRF token
yet), so those categories are not applicable here… a by-id document endpoint with no owner
concept"*. That was true when written and is now false: story #7's `/login` is live, so
documents are **owned**. All three endpoints require a Bearer access token, and a document
belonging to another account answers **404** — never 403, which would confirm the id exists.

This story's attack surface is therefore: an editor persisting user-authored HTML, a by-id
document endpoint **guarded by an owner predicate**, and a save endpoint bound to a JSON
body. CSRF stays out of scope (a Bearer token in a header is not sent ambiently by the
browser, so there is nothing for a cross-site form to ride). CORS/security-header checks
remain global, not per-story.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Account B (the attacker) | `qa.stranger@textery.test` / `Qa!Stranger2026` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, owned by A, `content` `<p>Первый абзац.</p>`, `version` `2` |
| Non-existent id | `00000000-0000-4000-8000-000000000000` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| Fixed messages | `NOT_FOUND` → `The requested resource was not found.`; `VERSION_CONFLICT` → `The document was modified by another save. Refetch and retry.`; `UNAUTHORIZED` → `A valid access token is required.`; `INTERNAL_ERROR` → `An unexpected error occurred. Please try again.` |
| Content limit | 200 000 Unicode code points; `MAX_REQUEST_BODY_BYTES` = `1_048_576` (1 MiB) |

---

## 1. Output Encoding (XSS)

### TC-05-SEC-1.1 — Editor content is served as sanitized markup, never raw executable HTML

| Field | Value |
|---|---|
| Description | Stored XSS: content is written by one user and rendered in another's browser (and in export). The editor UI is not the boundary — an attacker posts straight to the API. |
| Preconditions | Document A1 exists and is owned by account A, signed in. |
| Test data | Attack payload sent directly in the `PUT` body's `content`: `<p>Текст</p><script>alert(1)</script><img src=x onerror="alert(document.cookie)"><a href="javascript:alert(1)">ссылка</a>` |
| Steps | 1. `PUT /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` with that payload and the current `version`.<br>2. `GET /api/v1/documents/3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3` and read the raw `content` string.<br>3. Render the returned content in a browser. |
| Expected result | `200 OK`; the persisted and returned `content` contains no `<script` substring, no `onerror` (or any `on*`) attribute, and no `javascript:` URL — each is stripped or escaped by the server-side allowlist; the allowed `<p>Текст</p>` survives; step 3 executes no script and raises no alert. |
| Status | Not run |

---

## 2. Mass Assignment

### TC-05-SEC-2.1 — Server-owned fields cannot be set by the client on create or save

| Field | Value |
|---|---|
| Description | If `status`, `id` or `document_type` are bindable, a client can forge a completed document, target another id, or relabel a document — all through the ordinary editor endpoints. |
| Preconditions | Account A signed in; document A1 exists with `document_type` `реферат`, `status` `draft`. |
| Test data | Create body `{"document_type": "реферат", "status": "completed", "id": "11111111-1111-4111-8111-111111111111"}`; save body `{"content": "<p>Абзац</p>", "version": 2, "document_type": "эссе", "id": "11111111-1111-4111-8111-111111111111", "status": "completed"}` |
| Steps | 1. `POST /api/v1/documents` with the create body and a fresh `Idempotency-Key`; read the response.<br>2. `PUT /api/v1/documents/{A1}` with the save body.<br>3. `GET` both documents. |
| Expected result | Step 1 answers `201` with `status` `draft` and a server-generated `document_id` different from `11111111-…`; step 2 answers `200` applying only `content` and `version` (now `3`); step 3 shows document A1 still `document_type` `реферат`, `status` `draft`, id unchanged. The extra keys are silently ignored, not rejected — per `decisions/server-owned-fields-ignored-decision.md`. |
| Status | Not run |

---

## 3. Input Length Limits

### TC-05-SEC-3.1 — Oversized content is rejected before being persisted

| Field | Value |
|---|---|
| Description | The length check must run before sanitization and before any write: sanitizing first parses an adversarial payload before deciding to reject it. |
| Preconditions | Document A1 exists with `content` `<p>Первый абзац.</p>` and `version` `2`. |
| Test data | `content` = 200 001 Cyrillic characters; `version` = `2`; the check is measured NFC-normalized in code points, before sanitization |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that oversized content.<br>2. `GET /api/v1/documents/{A1}`.<br>3. Inspect the stored row directly. |
| Expected result | `400 Bad Request` with the `{"error_code", "message"}` shape; step 2 shows `content` `<p>Первый абзац.</p>` and `version` `2`; step 3 confirms no write reached storage — nothing truncated to 200 000 characters was persisted. |
| Status | Not run |

---

## 4. Non-Enumerable Resource Identifiers

### TC-05-SEC-4.1 — Document identifiers are not predictable across consecutive creations

| Field | Value |
|---|---|
| Description | Sequential ids let an attacker enumerate every document in the system and test the ownership guard against each one; a UUID v4 removes the address space. |
| Preconditions | Account A signed in. |
| Test data | Two consecutive `POST /api/v1/documents` `{"document_type": "реферат"}` calls, each with its own `Idempotency-Key` |
| Steps | 1. Create a document and record its `document_id`.<br>2. Create a second document and record its `document_id`.<br>3. Compare the two ids. |
| Expected result | Both ids are UUID v4 (version nibble `4`, variant `8`/`9`/`a`/`b`), not integers or auto-increment values; the second is not the first plus one and shares no incrementing prefix or timestamp segment — neither is derivable from the other. |
| Status | Not run |

---

## 5. Internal-Detail Disclosure

### TC-05-SEC-5.1 — Error responses never leak internal detail

| Field | Value |
|---|---|
| Description | A constraint message, an internal id shape, or Pydantic's default `input`/`loc` echo tells an attacker the schema, the ORM, and their own probe's reception — each a step toward a working payload. |
| Preconditions | Accounts A and B exist; document A1 exists and is owned by A. |
| Test data | Four probes: `GET` the non-existent id `00000000-0000-4000-8000-000000000000` (404); any request with no `Authorization` header (401); `POST /api/v1/documents` `{"document_type": "статья"}` (422) and an oversized `content` (400); `PUT` with a stale `"version": 1` (409) |
| Steps | 1. Issue each of the four probes.<br>2. Read every response body in full.<br>3. Search each body for a stack frame, a table/constraint name, a UUID echoed from the request, and the submitted field values. |
| Expected result | Every body is exactly `{"error_code": …, "message": …}` and nothing else — `404` → `NOT_FOUND` / `The requested resource was not found.`, `401` → `UNAUTHORIZED` / `A valid access token is required.`, `409` → `VERSION_CONFLICT` / `The document was modified by another save. Refetch and retry.`, `422`/`400` → their pinned codes with a generic message. No body contains a stack trace, a database constraint or relation name, an internal id shape (e.g. `document <uuid> not found`), a Pydantic `loc`/`input` key, or any value the client submitted. |
| Status | Not run |

### TC-05-SEC-5.2 — A database-unavailable failure also returns the same generic error shape, never a raw driver error

| Field | Value |
|---|---|
| Description | The infrastructure failure path is the one most likely to be missed by a handler and fall through to the framework's default, which prints the driver's connection string. |
| Preconditions | Account A signed in; Postgres made unreachable at the adapter boundary. |
| Test data | `POST /api/v1/documents` `{"document_type": "реферат"}` and `PUT /api/v1/documents/{A1}` `{"content": "<p>Абзац</p>", "version": 2}`, both issued during the outage |
| Steps | 1. Make Postgres unreachable.<br>2. Issue the create request and read the body in full.<br>3. Issue the save request and read the body in full.<br>4. Search both for `psycopg`, `sqlalchemy`, `Traceback`, `postgresql://`, a hostname, a port, and a password fragment. |
| Expected result | Both answer `500` with exactly `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` — the same shape as 5.1; none of the searched strings appears in either body, and neither carries a stack trace or a connection-string/credential fragment. |
| Status | Not run |

---

## 6. Oversized Payload Rejection

> **AMENDED 2026-07-17 — as originally written this scenario could not pass, or could
> only duplicate 5.2.** It demanded a body "at the size limit" accepted and "one byte
> past" rejected *before business logic*, while its own DSL row defined that limit as
> "200,000 characters plus envelope". Those are two different limits. A 200,000-character
> ASCII body is ~200 KB — nowhere near any sane body cap — so "one additional byte" is
> **not** stopped before business logic; it is stopped several steps later by the
> *character* check, which is exactly API scenario 5.2. The byte limit is now pinned
> explicitly and independently of the character limit.

`MAX_REQUEST_BODY_BYTES = 1_048_576` (1 MiB). Rationale: 200,000 characters of Cyrillic is
~400 KB in UTF-8; worst-case 4-byte code points plus HTML escaping and the JSON envelope
stay under 1 MiB. Deliberately slack — a byte cap that rejects legitimate content is worse
than one that admits 600 KB the character check then rejects with a precise 400.

### TC-05-SEC-6.1 — A request body at the size limit is accepted; one byte past it is rejected before parsing cost balloons

| Field | Value |
|---|---|
| Description | The byte cap exists so an attacker cannot make the server parse an arbitrarily large JSON body. It must fire in middleware, before the body is read and before any usecase runs — and it must not fire one byte early on a legitimate document. |
| Preconditions | Document A1 exists; the request-size middleware is configured with `MAX_REQUEST_BODY_BYTES = 1_048_576`; a mock usecase records whether it was invoked. |
| Test data | Body A: exactly `1 048 576` bytes. Body B: exactly `1 048 577` bytes (`Content-Length` = `MAX_REQUEST_BODY_BYTES + 1`). Both are well-formed save payloads for document A1. |
| Steps | 1. `PUT /api/v1/documents/{A1}` with body A.<br>2. `PUT /api/v1/documents/{A1}` with body B.<br>3. Assert on the mock usecase whether `execute` was awaited for each. |
| Expected result | Step 1 is **not** rejected for its size — it reaches the content check and answers either `200 OK` or `400` for the 200 000-character limit (a different limit, covered by API TC-05-API-5.2), never `413`. Step 2 answers `413 Payload Too Large`; the JSON body is never parsed and `execute.assert_not_awaited()` holds. |
| Status | Not run |

---

## 7. Broken Object-Level Authorization (IDOR)

> Added 2026-07-17 — see `decisions/document-ownership-decision.md`. This section did not
> exist while the story was anonymous; it is the attack surface that ownership creates.

### TC-05-SEC-7.1 — A document belonging to another account is indistinguishable from a missing one

| Field | Value |
|---|---|
| Description | Any difference between "foreign" and "missing" — status, code, message, or the ordering of the version check — re-creates the existence oracle the 404 exists to close, and a 404 that still reveals a correct version leaks more. |
| Preconditions | Accounts A and B exist; document A1 is owned by A at `version` `2`; account B is signed in. |
| Test data | Document A1 id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`; non-existent id `00000000-0000-4000-8000-000000000000`; B's save body `{"content": "<p>Захват</p>", "version": 2}` — the correct current version |
| Steps | 1. `GET /api/v1/documents/{A1}` as account B.<br>2. `GET /api/v1/documents/00000000-0000-4000-8000-000000000000` as account B; compare with step 1.<br>3. `PUT /api/v1/documents/{A1}` as account B with the correct-version body.<br>4. `GET /api/v1/documents/{A1}` as account A. |
| Expected result | Steps 1 and 2 both answer `404 Not Found` — never `403` — with the identical body `{"error_code": "NOT_FOUND", "message": "The requested resource was not found."}`; same status and same body dict, no per-branch `error_code`. Step 3 also answers `404`, never `409` — the foreign document never reaches the version check, so the response cannot reveal that `2` was correct. Step 4 shows account A's `content` `<p>Первый абзац.</p>` and `version` `2`, unchanged. |
| Status | Not run |

### TC-05-SEC-7.2 — Every document endpoint rejects an absent or unusable token

| Field | Value |
|---|---|
| Description | An endpoint that forgot the dependency, or one whose guard checks the signature but not the token `type` claim, accepts a long-lived refresh token as a document credential. |
| Preconditions | Account A has completed `POST /api/v1/auth/login` and holds both the access and refresh tokens of the pair; document A1 exists. |
| Test data | (a) No `Authorization` header. (b) `Authorization: Bearer <refresh_token>` — the refresh token from the login pair. Endpoints: `POST /api/v1/documents`, `GET /api/v1/documents/{A1}`, `PUT /api/v1/documents/{A1}` |
| Steps | 1. Call all three endpoints with no `Authorization` header.<br>2. Call all three with the refresh token as the Bearer credential.<br>3. Read each of the six response bodies. |
| Expected result | All six answer `401 Unauthorized` with `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}`; no call returns `200`, `201`, `404` or `422`; the refresh token is rejected by the `type`-claim guard in `read_access_subject` and is never accepted as a document credential. |
| Status | Not run |

### TC-05-SEC-7.3 — An idempotency key is scoped to its owner

| Field | Value |
|---|---|
| Description | A globally-scoped idempotency key is a cross-account disclosure: account B guessing (or reusing) A's key would be handed A's document as a "replay". |
| Preconditions | Accounts A and B both exist and are signed in. |
| Test data | The same header value for both: `Idempotency-Key: 3f0c8a9e-2b41-4d77-9c6a-b5e1d2704f88`; body `{"document_type": "реферат"}` for both |
| Steps | 1. `POST /api/v1/documents` as account A with that key; record `document_id` A.<br>2. `POST /api/v1/documents` as account B with the identical key and body; record `document_id` B.<br>3. `GET /api/v1/documents/{document_id B}` as account B. |
| Expected result | Both calls answer `201 Created`, not `200` — B's call is not treated as a replay of A's; `document_id` B differs from `document_id` A; B's response body discloses none of A's document (no id, no content, no timestamps of A's); step 3 returns B's own empty document. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `HTML-like markup submitted directly ... not through the editor` | `<script>`/`<img onerror=...>` sent directly in the `PUT` body's `content` field |
| `stripped or escaped` | server-side allowlist-based sanitizer applied before persist, re-applied/verified on render |
| `sets a status and an id` | `POST /api/v1/documents` body includes `status: "completed"`, `id: "<attacker-uuid>"` |
| `sets a document_type, an id, and a status` | `PUT /api/v1/documents/{document_id}` body includes those fields alongside `content`/`version` |
| `exceeds the maximum allowed length` | `content` longer than 200,000 characters |
| `not sequential or otherwise guessable` | `document_id` is a UUID v4, not an auto-increment integer |
| `a not-found, an unauthorized, a validation error, and a version conflict` | `404` (missing or foreign `document_id`), `401` (absent/invalid Bearer), `422`/`400` (bad `document_type`/oversized `content`), `409` (stale `version`) response bodies |
| `a stable, generic client-facing error shape` | **`{"error_code": "...", "message": "..."}`** — the shape story #7 already ships and `07-authorization/endpoints.md` declares. **Corrected 2026-07-17**: this row previously read `{"error": "..."}`, which no handler has ever produced, so the scenario could not be written against it. |
| `echo back the client's own submitted field values` | Pydantic v2's default `RequestValidationError` body includes `input` — the client's own value — plus `loc`; it must be overridden, not left at the framework default |
| `an internal id shape` | e.g. `NotFoundException(f"generation {id} not found")` reaching the client; 404/409 handlers must emit a fixed message and ignore `str(exc)` |
| `MAX_REQUEST_BODY_BYTES` | `1_048_576` (1 MiB), pinned in the request-size middleware. **A different limit from the 200,000-character content cap** — see the 6.1 amendment note. |
| `one byte past MAX_REQUEST_BODY_BYTES` | `Content-Length` = `MAX_REQUEST_BODY_BYTES + 1`; rejected with `413` by middleware before the JSON body is read |
| `the body is never parsed and no usecase is invoked` | asserted at the rest-adapter level with a mock usecase: `execute.assert_not_awaited()` |
| `raw driver/connection error text` | e.g. a raw Postgres connection-refused message or SQLAlchemy exception string |
| `two accounts` | two register→verify→login bootstraps, each yielding its own access token |
| `byte-identical to fetching an id that never existed` | same status **and** same body dict; a distinct `error_code` per branch would re-create the existence oracle 404 exists to close |
| `a refresh token rather than an access token` | the `refresh_token` from `POST /auth/login`'s pair, sent as `Authorization: Bearer <refresh_token>`; rejected by `read_access_subject`'s `type` claim guard |
