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

---

## 1. Output Encoding (XSS)

### 1.1 Editor content is served as sanitized markup, never raw executable HTML

```gherkin
Given a manual document whose saved content contains HTML-like markup submitted
  directly to the save endpoint (not through the editor's own formatting)
When the document's content is served to a client
Then any disallowed markup is stripped or escaped
And no injection payload executes as HTML in a client rendering the response
```

---

## 2. Mass Assignment

### 2.1 Server-owned fields cannot be set by the client on create or save

```gherkin
Given a manual-document creation request whose body also sets a status and an id
When the request is submitted
Then only the server-controlled defaults are ever persisted for those fields

Given a save request whose body also sets a document_type, an id, and a status
When the request is submitted
Then only the content and version fields are ever applied
```

---

## 3. Input Length Limits

### 3.1 Oversized content is rejected before being persisted

```gherkin
Given a save request whose content exceeds the maximum allowed length
When the request is submitted
Then the request is rejected before any write reaches storage
```

---

## 4. Non-Enumerable Resource Identifiers

### 4.1 Document identifiers are not predictable across consecutive creations

```gherkin
Given two manual documents are created one after another
Then their identifiers are not sequential or otherwise guessable from one another
```

---

## 5. Internal-Detail Disclosure

### 5.1 Error responses never leak internal detail

```gherkin
Given requests that trigger a not-found, an unauthorized, a validation error, and a
  version conflict on the document endpoints
When each response is returned to the client
Then each response body exposes only a stable, generic client-facing error shape
And none of them include a database constraint message, an internal id shape, or a
  stack trace
And none of them echo back the client's own submitted field values
```

### 5.2 A database-unavailable failure also returns the same generic error shape, never a raw driver error

```gherkin
Given the database is unreachable when a client submits a document creation or save
  request
When the failure response is returned to the client
Then the response body matches the same generic client-facing error shape as 5.1
And it includes no stack trace, no raw driver/connection error text, and no
  connection-string or credential fragment
```

---

## 6. Oversized Payload Rejection

### 6.1 A request body at the size limit is accepted; one byte past it is rejected before parsing cost balloons

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

```gherkin
Given a document save request whose body is exactly MAX_REQUEST_BODY_BYTES
When the client submits it
Then the request is not rejected for its size
  (it may still be rejected by the 200,000-character content check — a different limit,
   covered by API 5.2)

Given a document save request whose body is one byte past MAX_REQUEST_BODY_BYTES
When the client submits it
Then the response is 413
And the body is never parsed and no usecase is invoked
```

---

## 7. Broken Object-Level Authorization (IDOR)

> Added 2026-07-17 — see `decisions/document-ownership-decision.md`. This section did not
> exist while the story was anonymous; it is the attack surface that ownership creates.

### 7.1 A document belonging to another account is indistinguishable from a missing one

```gherkin
Given two accounts, and a document created by the first
When the second account fetches that document's id
Then the response reports not found, not forbidden
And the response is byte-identical to fetching an id that never existed

Given the same two accounts and document
When the second account submits a save for that document's id, using the document's
  correct current version
Then the response reports not found, not forbidden
And the response does not reveal that the submitted version was correct
And the first account's content is unchanged
```

### 7.2 Every document endpoint rejects an absent or unusable token

```gherkin
Given no Authorization header
When the client creates, fetches, or saves a document
Then each response is 401 with the generic error shape

Given an Authorization header carrying a refresh token rather than an access token
When the client creates, fetches, or saves a document
Then each response is 401
And the refresh token is never accepted as a document credential
```

### 7.3 An idempotency key is scoped to its owner

```gherkin
Given two accounts submit a document creation request with the identical
  Idempotency-Key value
When both requests are submitted
Then each account receives its own separate document
And neither response discloses the other account's document
```

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
