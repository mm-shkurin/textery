<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Мои проекты — Security Tests

Attack surface: one owner-scoped read whose filtering, ordering and searching are all
driven by client input, one write that names a resource by id, and user-authored text
rendered into two new surfaces. Generic 401 handling, security headers, CORS and HTTPS are
cross-cutting and tested globally — not here.

---

## 1. Owner Scoping

### 1.1 No parameter combination reveals another account's rows
```gherkin
Given another account with documents and generations
When the caller requests their projects across every sort order, several pages, and a search term matching the other account's rows
Then no item belonging to the other account is ever returned
```

### 1.2 The reported total counts only the caller's rows
```gherkin
Given another account with many projects
When the caller requests their own projects
Then the reported total counts only their own
```

### 1.3 An owner supplied by the client is ignored
```gherkin
Given an authenticated user
When they request their projects while supplying another account's owner identity
      in the query, the body, and a header
Then their own feed is returned
And the supplied identity has no effect
```

---

## 2. Injection

### 2.1 Search input reaching the query cannot alter it
```gherkin
Given an authenticated user
When they search using SQL metacharacters, quote-breaking payloads, comment sequences
      and statement terminators
Then the search returns matches for the literal text or nothing
And no error exposing query structure is returned
And their other projects remain intact
```

### 2.2 Wildcards cannot widen the search
```gherkin
Given a search term consisting of pattern metacharacters and the escape character
When the caller searches for it
Then only items containing those characters literally are returned
```

### 2.3 A sort value cannot reach the query as a column name
```gherkin
Given an authenticated user
When they request their projects with a sort value crafted to look like a column expression
Then the request is refused as a bad request
And no ordering derived from that value is applied
```

---

## 3. Stored Cross-Site Scripting and Output Encoding

### 3.1 Markup stored in any echoed field is neutralized
```gherkin
Given a document whose title carries a script payload
And a document whose body carries a script payload
And a generation whose topic carries a script payload
When the caller requests their projects
Then every echoed field is returned neutralized
And rendering the feed in both views executes nothing
```

### 3.2 A preview cut from stored markup cannot reopen a tag
```gherkin
Given a document whose stored markup would be cut mid-tag at the preview limit
When the caller requests their projects
Then the preview carries no markup at all
```

### 3.3 The echoed search query renders as text
```gherkin
Given a search term carrying script markup
When the user searches for it
Then the query is echoed as text
And no script executes
```

---

## 4. Broken Object-Level Authorization

### 4.1 Retrying another account's generation is refused indistinguishably
```gherkin
Given a failed generation owned by another account
When the caller retries it
Then the request is refused as not found
And the response is byte-identical to an identifier that does not exist
And no generation is created for either account
```

### 4.2 An idempotency key cannot reach another account's record
```gherkin
Given another account has used a given idempotency key
When the caller retries their own failed generation with that same key
Then their own generation is created
And nothing belonging to the other account is returned
```

---

## 5. Mass Assignment

### 5.1 The retry cannot set server-owned fields
```gherkin
Given the caller owns a failed generation
When they retry it while supplying an owner, status, identifier or creation time
Then the new generation is owned by the caller
And carries a server-assigned status and identifier
And none of the supplied values is stored
```

### 5.2 Server-owned list fields cannot be supplied by the caller
```gherkin
Given a list request supplying a preview, a kind, and an owner
When the caller requests their projects
Then the returned items carry server-derived values
And the supplied ones are ignored
```

---

## 6. Abuse Limits

### 6.1 One source generation cannot be retried without bound
```gherkin
Given the caller owns a failed generation
When they retry it repeatedly with fresh idempotency keys past the ceiling
Then further retries are refused as too many requests
And no further generation is created
```

### 6.2 Search cannot be used to occupy the database
```gherkin
Given an authenticated user
When they issue searches faster than the per-account allowance
Then the excess is refused as too many requests
And every accepted request is answered or refused within the statement deadline
And other accounts' requests are unaffected
```

---

## 7. Information Disclosure

### 7.1 Failures expose nothing internal
```gherkin
Given a projects request that fails at the database
When the error is returned
Then it carries only a generic code, message and correlation identifier
And exposes no query text, table name, stack frame or file path
```

### 7.2 Credentials, keys and user text never reach the log
```gherkin
Given a sentinel value planted in the bearer token, the idempotency key, the search
  query and a document's title and body
When the statement deadline trips and when the database is unavailable
Then no sentinel appears in the response body
And no sentinel appears in the captured log output
And each redacted field is present as a fixed redaction marker
```

### 7.3 An unmapped failure returns the sanctioned envelope
```gherkin
Given an unmapped exception raised while the feed is built
When the response is returned
Then the body matches the sanctioned error schema
And it contains no stack trace, database keyword, internal class name or file path
```

---

## 8. Server-Derived Fields

### 8.1 A client-supplied preview is ignored
```gherkin
Given a list request that also supplies a preview value
When the feed is returned
Then every preview is derived from stored content
And nothing supplied by the client appears in any preview
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `supplying another account's owner identity` | `?owner_id=…` as query param, body field, and `X-Owner-Id` header — must be ignored, not honoured |
| `refused as a bad request` | 400 `INVALID_SORT` with `{error_code, message}` |
| `refused as too many requests` | 429 `SEARCH_BUSY` / `RETRY_LIMIT_REACHED` |
| `byte-identical` | Same status, headers and body bytes for absent and foreign (404) |
| `pattern metacharacters` | `%`, `_`, and the `ESCAPE` character |
| `no script executes` | Rendered as escaped text; no dialog, no injected node |
| `a sentinel value` | A marker string planted in the DB error path and in document content |
| `a fixed redaction marker` | Fixed redaction token plus a correlation id |
| `the statement deadline` | 3 s, `SET LOCAL` per request |
| `the ceiling` | 5 retries per source generation |
