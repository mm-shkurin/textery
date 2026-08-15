<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — prerequisite guards → idempotent+race-safe
> conversion → validation → output safety.

# Generate → edit — API Tests

Endpoint: `POST /api/v1/documents/from-generation`. Reused endpoints covered by stories 1 and 5.

## 1. Prerequisite Guards

### 1.1 Conversion of a non-existent generation is refused
```gherkin
Given an authenticated user
When they request conversion for a generation id that does not exist
Then the request is refused as not found
And no document is created
```

### 1.2 Conversion of another account's generation is refused indistinguishably
```gherkin
Given a generation completed by another account
When the caller requests its conversion
Then the request is refused as not found
And the response is byte-identical to the non-existent case
And no document is created
```

### 1.3 Conversion of a not-completed generation is refused (each non-terminal state)
```gherkin
Given a generation owned by the caller in a non-completed state <state>
When they request its conversion
Then the request is refused as a conflict
And no document is created
```
Cover each edge separately: <state> ∈ {pending, in_progress, failed}.

### 1.4 Conversion of a generation in an unknown status fails closed
```gherkin
Given a generation owned by the caller whose status is not a recognised value
When they request its conversion
Then the request is refused as a conflict
And no document is created
And conversion is never attempted
```

## 2. Convert — Happy Path

### 2.1 A completed generation converts to an editable document
```gherkin
Given a completed generation owned by the caller
When they request its conversion with an idempotency key
Then a document is created linked to that generation
And the document version is the initial version
And the response carries a server-derived title and sanitized HTML content
```

### 2.2 The converted document is retrievable and editable
```gherkin
Given a document created from a generation
When the owner opens it and saves an edit
Then the edit is persisted like a manual document
```

## 3. Idempotency & Race Safety

### 3.1 Replaying the same idempotency key returns the same document
```gherkin
Given a completed generation already converted with an idempotency key
When the same key is replayed
Then the existing document is returned
And no second document is created
```

### 3.2 A repeat conversion for the same generation returns the same document
```gherkin
Given a generation already converted to a document
When conversion is requested again for that generation with a new key
Then the existing document is returned
And no second document is created
```

### 3.3 Two concurrent conversions of one generation yield exactly one document
```gherkin
Given a completed generation not yet converted
And two conversion requests held at a barrier at the check-then-insert window
When both are released together
Then exactly one document exists for that generation
And the losing request returns that same document, not an error
```

### 3.4 A failure mid-conversion leaves no partial state
```gherkin
Given a completed generation
When the conversion write fails partway through
Then no document row exists for that generation
And no idempotency marker is left that would block a later retry
```

### 3.5 A stale save of a generated document is rejected
```gherkin
Given a document created from a generation opened in two sessions at the same version
When the first session saves and then the second saves against the stale version
Then the second save is rejected as a version conflict
And the first session's edit is not overwritten
```

### 3.6 Pathological markdown converts within a bounded time
```gherkin
Given a completed generation whose content is deeply nested markdown under the size limit
When it is converted
Then conversion completes within a wall-clock bound (or is rejected on nesting depth)
And no worker hangs
```

## 4. Validation

### 4.1 Server-owned fields in the body are ignored
```gherkin
Given a completed generation owned by the caller
When conversion is requested with a body also carrying title, id, status, version, and a foreign generation id
Then the linked generation is the authorized one only
And title, id, status, and version are the server-derived values, not the submitted ones
```

### 4.2 A manual document creation rejects a client-supplied generation link
```gherkin
Given an authenticated user
When they create a blank document with a body carrying a generation id
Then the created document has no generation link
```

### 4.3 Converted content over the limit is rejected at the boundary
```gherkin
Given a generation whose converted content would exceed the content limit measured in Unicode code points
When conversion is requested
Then the request is refused
And the content is never truncated
And no document is created
```

### 4.4 Source content is bounded before the parser runs
```gherkin
Given a generation whose source content is far past any sane bound
When conversion is requested
Then it is refused before the full parse-and-sanitize work is performed
```

## 5. Content Fidelity & Output Safety

### 5.1 Multibyte content round-trips byte-exact
```gherkin
Given a completed generation whose content mixes Cyrillic, an emoji, and a combining accent
When it is converted and then read back
Then the read content equals the source after Unicode normalization, byte for byte
```

### 5.2 Script and event-handler markup is neutralized
```gherkin
Given a generation whose content contains a script tag and an element event handler
When it is converted
Then the stored and rendered content contain neither
```

### 5.3 Dangerous URL schemes are neutralized
```gherkin
Given a generation whose content contains a javascript link, a data-uri link, and an image with an error handler
When it is converted
Then the emitted links and image sources are stripped or made safe
```

### 5.4 A sanitizer or parser failure fails closed
```gherkin
Given a generation whose conversion makes the parser or sanitizer error
When conversion is requested
Then the request fails
And no document is created
And nothing unsanitized is stored
```

### 5.6 Markup and schemes are stripped regardless of case, under a hostile locale
```gherkin
Given content with mixed-case markup and schemes (a SCRIPT tag, a JavaScript link)
And the server runs under a locale whose case-folding differs from the default
When it is converted
Then the markup and schemes are still stripped
```

### 5.5 Error bodies expose no internal detail
```gherkin
Given seeded internal sentinels reachable by a failing conversion (a database message, an id shape, and a stack frame)
When each failure path is triggered — including the parser-failure family
Then no sentinel appears in the response body or the logs
And any internal detail is redacted to a fixed token, not merely re-encoded
And each error body matches the sanctioned generic error shape
```
