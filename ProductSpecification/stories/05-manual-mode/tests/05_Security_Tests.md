# Manual input mode (non-AI document creation) — Security Tests

Scope note: this story is fully anonymous (no auth, no JWT, no session/CSRF token yet),
so those categories are not applicable here. Generic 401/CORS/security-header checks are
handled globally, not per-story. Scenarios below target this story's actual attack
surface: an editor persisting user-authored HTML, a by-id document endpoint with no
owner concept, and a save endpoint bound to a JSON body.

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
Given requests that trigger a not-found, a validation error, and a version conflict on
  the document endpoints
When each response is returned to the client
Then each response body exposes only a stable, generic client-facing error shape
And none of them include a database constraint message, an internal id shape, or a
  stack trace
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

```gherkin
Given a document creation or save request body at the maximum size the endpoint
  accepts (bounded by the pinned 200,000-character content limit plus a fixed
  envelope overhead)
When the client submits it
Then the request is accepted

Given the same request with one additional byte pushing it past that limit
When the client submits it
Then the request is rejected before it reaches business logic
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
| `a not-found, a validation error, and a version conflict` | `404` (missing `document_id`), `422`/`400` (bad `document_type`/oversized `content`), `409` (stale `version`) response bodies |
| `a stable, generic client-facing error shape` | consistent error schema (e.g. `{"error": "..."}`) with no raw exception text |
| `the maximum size the endpoint accepts` | JSON envelope containing `content` at exactly 200,000 characters plus the fixed field overhead (`version`/`document_type` etc.) |
| `the same request with one additional byte` | identical fixture with one extra character appended, pushing total request size past the pinned limit |
| `raw driver/connection error text` | e.g. a raw Postgres connection-refused message or SQLAlchemy exception string |
