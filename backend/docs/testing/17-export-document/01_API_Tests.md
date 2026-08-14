<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — prerequisite/format guards → happy path →
> filename & encoding → safety (SSRF, deadline, disclosure).

# Export document — API Tests

Endpoint: `GET /api/v1/documents/{id}/export?format=pdf|docx`. Read-only.

## 1. Prerequisite & Format Guards

### 1.1 Export of a non-existent document is refused
```gherkin
Given an authenticated user
When they export a document id that does not exist
Then the request is refused as not found
And no file is returned
```

### 1.2 Export of another account's document is refused indistinguishably
```gherkin
Given a document owned by another account
When the caller exports it
Then the request is refused as not found
And the response is byte-identical to the non-existent case
```

### 1.3 An unsupported or missing format is refused
```gherkin
Given a document owned by the caller
When they export it with a format that is neither pdf nor docx, or with no format
Then the request is refused as unprocessable
And no file is returned
```

## 2. Happy Path

### 2.1 A document exports as a valid PDF
```gherkin
Given a document owned by the caller
When they export it as pdf
Then the response is a valid PDF with the pdf content type
And is delivered as an attachment
```

### 2.2 A document exports as a valid DOCX
```gherkin
Given a document owned by the caller
When they export it as docx
Then the response is a valid DOCX with the wordprocessingml content type
And is delivered as an attachment
```

### 2.3 An empty document exports to a valid file
```gherkin
Given a document owned by the caller with empty content
When they export it
Then a valid near-empty file is returned, not an error
```

### 2.4 Export does not mutate the document
```gherkin
Given a document owned by the caller at a known version
When they export it
Then the document version is unchanged afterwards
```

## 3. Filename & Encoding

### 3.1 The filename is derived from the title, encoded for Cyrillic
```gherkin
Given a document whose title contains Cyrillic characters
When it is exported
Then the attachment filename is RFC 5987-encoded and reflects the title
```

### 3.2 A document with no title uses a default filename
```gherkin
Given a document with no title
When it is exported
Then the attachment filename is a defined default, never empty or null
```

### 3.3 A title with header-breaking characters cannot inject into the header
```gherkin
Given a document whose title contains carriage returns, line feeds, and quotes
When it is exported
Then those characters are stripped or encoded
And the response headers are not broken out of
```

### 3.4 Multibyte content renders intact
```gherkin
Given a document whose content mixes Cyrillic, an emoji, and a combining accent
When it is exported to pdf and to docx
Then the multibyte characters render intact with no mojibake or replacement characters
```

### 3.5 A save immediately followed by an export reflects the latest content
```gherkin
Given a document just saved with new content and title
And the read path is made to model replication or cache lag
When it is exported right away
Then the file reflects the just-committed content and title, read through the primary
```
Note: if the deployment has no read replica, record that reads are single-primary and the lag model is unnecessary.

### 3.6 A long multibyte title is truncated on a grapheme boundary
```gherkin
Given a document whose title is long enough to hit the filename length cap and contains Cyrillic and emoji
When it is exported
Then the filename is truncated on a grapheme boundary with no split sequence
```
Note: if there is no filename length cap, record that explicitly instead of this scenario.

## 4. Safety

### 4.1 Embedded external URLs do not cause an outbound request
```gherkin
Given a document whose content references an external image URL
When it is exported to pdf
Then the renderer makes no outbound network request
And the export still completes
```

### 4.2 A pathological document aborts within the render deadline
```gherkin
Given a document engineered to exceed the render deadline
And an injectable clock at the deadline boundary
When it is exported just under the deadline
Then it completes and the worker is freed
When it is exported just over the deadline
Then it aborts with the sanctioned error and the worker is freed, no detached render
```

### 4.5 An over-limit document cannot drive an unbounded render
```gherkin
Given a document whose stored content is past the content limit
When it is exported
Then export rejects or clamps it at its own boundary
And does not render unbounded content in memory
```
Note: if the content limit is guaranteed at save (story 5) so an over-limit row is unreachable, record that guarantee as the guard instead.

### 4.3 Error bodies expose no internal detail
```gherkin
Given seeded internal sentinels reachable by a failing export (a filesystem path, a database message, a stack frame)
When each failure path is triggered
Then no sentinel appears in the response body or the logs
And each error body matches the sanctioned generic error shape
```

### 4.4 A render failure emits an attributable signal
```gherkin
Given an export whose render fails
When it is triggered
Then a server-side signal keyed by the document id is emitted
And a successful export emits no such signal
```
