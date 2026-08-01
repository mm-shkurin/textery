# Мои проекты — Security Tests

The story's attack surface is one free-text parameter that reaches a SQL pattern match,
one resource addressed by id, and user-authored text rendered into two new surfaces.
Generic 401s, headers, CORS, and HTTPS are cross-cutting and tested globally, not here.

---

## 1. Authorization

### 1.1 The feed cannot be widened to another account
```gherkin
Given a caller authenticated as one account
When they request their projects while supplying another account's owner identity
      in the query, the body, and a header
Then only their own items are returned
```

### 1.2 A repeat cannot be aimed at another account's generation
```gherkin
Given a generation owned by another account
When the caller requests a repeat of it
Then the answer is identical to one for a generation that does not exist
And no generation is created
```

---

## 2. Injection

### 2.1 Search text cannot alter the query
```gherkin
Given search terms carrying quote, comment, and statement-terminator sequences
When the caller searches for each in turn
Then each is treated as literal text
And the feed and its data are unchanged
```

### 2.2 Wildcards cannot widen the search
```gherkin
Given a search term consisting of pattern metacharacters and an escape character
When the caller searches for it
Then only items containing those characters literally are returned
```

---

## 3. Output Encoding

### 3.1 Scripted titles and previews render as text
```gherkin
Given a document whose title and body carry script markup
When the user opens «Мои проекты» in both views
Then the markup is shown as text
And no script executes
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

## 4. Mass Assignment

### 4.1 Server-owned list fields cannot be supplied by the caller
```gherkin
Given a request supplying a preview, a kind, and an owner
When the caller requests their projects
Then the returned items carry server-derived values
And the supplied ones are ignored
```

---

## 5. Disclosure

### 5.1 Failures expose no internals
```gherkin
Given a seeded internal marker in the failing query's error
When the caller triggers a rejected request, a search timeout, and an unexpected failure
Then no answer carries the marker, a query fragment, or a stack frame
And the logs carry the marker only in redacted form
```

### 5.2 Totals count only the caller's work
```gherkin
Given two accounts owning different numbers of projects
When one of them requests their projects
Then the reported total counts only their own items
```

---

## 6. Abuse

### 6.1 Search cannot be used to hold the database
```gherkin
Given a search crafted to be maximally expensive
When it is requested repeatedly
Then each request is answered or refused within the search timeout
And the service keeps serving other requests
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|--------------------------|
| `supplying another account's owner identity` | `owner_id` as query param, body field, and `X-Owner-Id` header |
| `identical to one for a generation that does not exist` | Byte-identical status and body (404) |
| `pattern metacharacters` | `%`, `_`, and the `ESCAPE` character |
| `no script executes` | Rendered as escaped text; no dialog, no injected node |
| `a seeded internal marker` | A sentinel string planted in the DB error path and in document content |
| `redacted form` | Fixed redaction token plus a correlation id |
| `the search timeout` | `projects_search_statement_timeout_ms` |
