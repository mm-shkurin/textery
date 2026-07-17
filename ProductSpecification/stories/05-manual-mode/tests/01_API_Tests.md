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
<access_token>`, so every test's Given implies a register → verify → login bootstrap, and
the account is `POST /documents`'s parent resource. Ownership scenarios are in section 9;
the 401 and cross-account cases live in `05_Security_Tests.md` section 7.

---

## 1. Create Document — Validation

### 1.1 Reject unsupported document type

```gherkin
Given a manual-document creation request with a document type other than the 4
  supported values
When the client submits the request
Then the response is rejected as unprocessable
And no document is created
```

### 1.2 Ignore server-owned fields in the request body

```gherkin
Given a manual-document creation request whose body also sets a status, an id, and
  non-empty content
When the client submits the request
Then the created document's status is "draft", not the attacker-supplied value
And the created document's id is server-generated, not the attacker-supplied value
And the created document's content is empty, not the attacker-supplied value
```

---

## 2. Create Document — Happy Path

### 2.1 Creating a manual document returns immediately with no linked generation

```gherkin
Given a valid manual-document creation request for a supported document type
When the client submits the request
Then the response confirms the document was created
And the document's status is "draft" with empty content
And the response is returned synchronously, with no polling required
And no generation record is created or linked to the document
```

---

## 3. Create Document — Re-run Safety (idempotency)

### 3.1 Replaying the same idempotency key does not create a duplicate document

```gherkin
Given a valid manual-document creation request submitted with idempotency key "key-1"
And the request has already been accepted once
When the client submits the identical request again with idempotency key "key-1"
Then the response refers to the original document, not a new one
And exactly one document exists for that idempotency key
```

---

## 4. Get Document

### 4.1 Fetching a freshly created document returns its empty state

```gherkin
Given a manual document that has just been created
When the client fetches it
Then the response shows empty content and a version token
```

### 4.2 Requesting a non-existent document reports not found

```gherkin
Given no document exists with a given id
When the client fetches that id
Then the response reports the document was not found
```

---

## 5. Save Document — Validation

### 5.1 Reject content exceeding the maximum length

```gherkin
Given a manual document exists
And a save request whose content exceeds the maximum allowed length
When the client submits the save request
Then the response is a validation error
And the document's stored content is unchanged
And the content is never silently truncated to fit
```

### 5.2 Accept content exactly at the maximum length, reject one character past it

```gherkin
Given a manual document exists
And a save request whose content is exactly at the maximum allowed length
When the client submits the save request
Then the request is accepted

Given a save request whose content is one character past the maximum allowed length
When the client submits the save request
Then the response is a validation error
```

### 5.3 Saving against a non-existent document reports not found

```gherkin
Given no document exists with a given id
When the client submits a save request for that id
Then the response reports the document was not found
```

### 5.4 Ignore server-owned fields in the save request body

```gherkin
Given a manual document exists
And a save request whose body also sets a document_type, an id, and a status
When the client submits the save request
Then only the content and version fields are ever applied
And the document's type, id, and status remain unchanged
```

---

## 6. Save Document — Happy Path & Concurrency

### 6.1 Saving persists the editor content and returns the updated state

```gherkin
Given a manual document exists with empty content and a known version
When the client saves formatted content (headings, a list, bold, italic) using that
  version
Then the response confirms the save
And the document's version has advanced
And reopening the document shows the same formatted content that was saved
```

### 6.2 Saving the same content and version twice is idempotent

```gherkin
Given a manual document has just been saved with certain content and a resulting
  version
When the client submits the exact same save request again
Then the response confirms the same stored state
And no duplicate write or duplicate version advance occurs
```

### 6.3 A save against a stale version is rejected, never silently overwriting

```gherkin
Given a manual document has been saved once, advancing its version
When a second save is submitted using the document's original, now-stale version
Then the response reports a version conflict
And the content from the first save remains intact
And the second save's content is not silently written over it
```

### 6.4 An entirely Cyrillic, multi-paragraph document round-trips without corruption

```gherkin
Given a manual document exists
When the client saves content that is entirely Cyrillic across multiple formatted
  paragraphs, headings, and a list
Then reopening the document renders the exact same text, with no encoding corruption
And no character is dropped at a multibyte-character boundary
```

### 6.5 The max-length boundary never splits a multibyte character, including outside the BMP

```gherkin
Given a manual document exists
When the client saves content engineered so that the 200,000-character boundary lands
  in the middle of a multi-code-unit character (an emoji or combining-accent sequence
  outside the Basic Multilingual Plane)
Then the boundary check counts whole characters/graphemes, never splitting one in half
And a save of content entirely composed of such characters, at or under the limit,
  round-trips exactly with no corruption
```

### 6.6 Canonically-equivalent Unicode content is compared consistently for duplicate-save detection

```gherkin
Given a manual document has just been saved with certain visible text
When the client resubmits the same version with the same visible text encoded using a
  different Unicode normalization form (NFC vs. NFD for the same combining-accent
  characters)
Then the save is handled consistently — either recognized as the same content with no
  spurious version advance, or treated as a distinct write and stored correctly either
  way — never silently corrupting the comparison or the stored result
```

### 6.7 Same-instant concurrent saves against one document resolve atomically, exactly one wins

> **Fixture amended 2026-07-17 — the two requests must carry DISTINCT content.** As
> originally written this scenario was mutually unsatisfiable with 6.2. 6.2 requires an
> identical `(content, version)` resubmit to answer **200** with no version advance, which
> forces the save path to treat "the stored content already equals mine and the version
> advanced by exactly one" as a replay rather than a conflict. If 6.7's two concurrent
> requests carried *identical* content, the loser would match that very rule and get 200 —
> while 6.7 demands a conflict. Distinct content separates the two: the loser's content
> does not match what landed, so it is a genuine conflict. Without this the implementation
> must fail one scenario or the other, whichever is written second.

```gherkin
Given a manual document exists at a known version
When two save requests carrying different content, both using that same version, are
  released to execute at the same instant against the same document
Then exactly one save succeeds and advances the version
And the other observes a version conflict, never a silently lost or corrupted write
And the stored content is exactly the winner's, never interleaved or partially applied
And this holds even when the two requests are handled by different backend instances
```

---

## 8. Save Document — Version Field Validation

### 8.1 A negative or non-integer version is rejected as invalid, not treated as a valid token

```gherkin
Given a manual document exists
When the client submits a save request with version -1
Then the response is a validation error

Given a manual document exists
When the client submits a save request with a non-integer version value
Then the response is a validation error
```

---

## 7. Save Document — Content Safety

### 7.1 Raw script/event-handler HTML submitted directly is neutralized, not stored verbatim

```gherkin
Given a manual document exists
When the client saves content containing raw script tags and event-handler
  attributes, submitted directly rather than through the editor's own formatting
Then the stored and returned content is sanitized
And no executable markup is ever served back to a client
```

### 7.2 When sanitization alters submitted content, the response reflects what was actually stored

```gherkin
Given a manual document exists
When the client saves content containing disallowed tags or attributes that get
  stripped by sanitization
Then the save response and a subsequent read both show the sanitized version
And neither response looks identical to the raw, unsanitized submission
```

---

## 9. Document Ownership

> Added 2026-07-17 — see `decisions/document-ownership-decision.md`. The cross-account and
> missing-token cases live in `05_Security_Tests.md` section 7; these are the owner-scoping
> rules the happy paths depend on.

### 9.1 A created document belongs to the authenticated account

```gherkin
Given an authenticated account
When the client creates a manual document
Then the document is owned by that account
And the owner is taken from the access token, never from the request body
```

### 9.2 A fetch returns only the authenticated account's own document

```gherkin
Given an authenticated account owning a document
When that account fetches the document
Then the response returns it

Given a second authenticated account
When the second account fetches the first account's document id
Then the response reports not found
```

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
