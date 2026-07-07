# Auto-generate: доклад — Security Tests

Scope note: this story is fully anonymous (no auth, no JWT, no session/CSRF token yet —
see `known-debt.md` #2), so those categories are not applicable here. Generic 401/CORS/
security-header checks are handled globally, not per-story. Scenarios below target this
story's actual attack surface: free-text fields reaching storage and an LLM prompt, a
publicly-callable paid external API, and a by-id lookup with no owner concept.

---

## 1. Injection Safety

### 1.1 Injection payloads in free-text fields are stored and returned safely

```gherkin
Given a generation request whose topic, requirements, and extra wishes contain
  injection-style payloads (SQL metacharacters, script tags)
When the request is submitted and later read back
Then the stored values are treated as inert data, not executed as code or queries
And no injection payload escapes into a database error or a broken query
```

---

## 2. Output Encoding (XSS)

### 2.1 Document content and echoed input are served as escaped text

```gherkin
Given a completed generation whose document content contains HTML-like markup
  (either from the user's own input or from the generation provider's output)
When the generation's content is served to a client
Then the markup is rendered as literal text, never as executed HTML
```

---

## 3. Mass Assignment

### 3.1 Server-owned fields cannot be set by the client

```gherkin
Given a generation request whose body also sets a status, an id, a creation timestamp,
  and a document type the client is not allowed to choose freely
When the request is submitted
Then only the server-controlled defaults are ever persisted for those fields
```

---

## 4. Input Length Limits

### 4.1 Oversized free-text fields are rejected before reaching the generation provider

```gherkin
Given a generation request whose requirements or extra wishes exceed the maximum
  allowed length
When the request is submitted
Then the request is rejected before any call to the generation provider is made
```

---

## 5. Non-Enumerable Resource Identifiers

### 5.1 Generation identifiers are not predictable across consecutive creations

```gherkin
Given two generations are created one after another
Then their identifiers are not sequential or otherwise guessable from one another
```

---

## 6. Secret & Internal-Detail Disclosure

### 6.1 A generation-provider failure never leaks credentials or raw upstream detail

```gherkin
Given the generation provider call fails and the failure reaches the client-visible
  generation record
When a client reads that generation's status
Then no provider credential appears in the response
And no raw upstream error body appears in the response
And the captured server logs for that failure show a fixed redaction marker in place
  of the credential, never the raw secret value
```

---

## 7. Resource Exhaustion / Cost-Amplification Guard

### 7.1 A flood of submissions cannot drive unbounded concurrent provider calls

```gherkin
Given far more generation requests are submitted than the configured worker
  concurrency ceiling
When all of them are queued
Then the number of concurrently-running generation-provider calls never exceeds
  the configured ceiling
```

---

## 8. Header Injection

### 8.1 A malformed idempotency key is rejected, not passed through

```gherkin
Given a request whose idempotency key contains header-breaking control characters
When the client submits the request
Then the request is rejected
And no malformed value reaches downstream storage or logs
```

---

## 9. Oversized Payload Rejection

### 9.1 A request with deeply nested or oversized JSON is rejected before parsing cost balloons

```gherkin
Given a request body far larger than any legitimate generation request
When the client submits it
Then the request is rejected before it reaches business logic
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `injection-style payloads` | strings like `'; DROP TABLE--`, `<script>alert(1)</script>` in `topic`/`requirements`/`extra_wishes` |
| `treated as inert data` | parameterized queries (SQLAlchemy), no string-concatenated SQL |
| `HTML-like markup` | `<img onerror=...>`/`<script>` sequences in stored content or a stubbed provider response |
| `rendered as literal text` | HTML-escaped on output, `Content-Type: application/json` (no HTML execution context server-side) |
| `sets a status, an id, a creation timestamp, and a document type the client is not allowed to choose` | body includes `status`, `id`, `created_at`, and `document_type` outside the supported enum |
| `exceed the maximum allowed length` | `requirements`/`extra_wishes` > 2000 chars |
| `not sequential or otherwise guessable` | `generation_id` is a UUID v4, not an auto-increment integer |
| `no provider credential appears in the response` | `OPENROUTER_API_KEY` absent from `GET /generations/{id}` body |
| `no raw upstream error body appears` | provider error mapped to a generic `failed` status, not passed through verbatim |
| `captured server logs ... show a fixed redaction marker` | log appender capture asserts a token like `[REDACTED]` in place of the key, not merely the absence of the raw string |
| `far more ... than the configured worker concurrency ceiling` | burst of requests >> `arq` `max_jobs` |
| `header-breaking control characters` | `Idempotency-Key: key\r\nX-Injected: 1` or similar CRLF sequence |
| `a request body far larger than any legitimate generation request` | JSON body with deeply nested objects or megabytes of payload, sent to `POST /api/v1/generations` |
