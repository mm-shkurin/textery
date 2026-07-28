> **Implementation Order**: sections 6-7, the last of the API sequence — implement after
> `01_API_Tests.md` and `01_API_Tests_Lifecycle.md`.

# AI chat editing — API Tests (applying the edit, history, quota)

DSL reference: see the table at the end of `01_API_Tests.md`.

## 6. Applying the Edit

### 6.1 The document, revision, message and terminal event commit as one unit
```gherkin
Given an edit whose model result is ready
When the final write fails
Then no revision exists without its assistant message
And no version increment exists without its revision
And the edit ends in a terminal error
```

### 6.2 A client that sees done immediately observes the version it was told
```gherkin
Given a caller reading an edit's stream
When the terminal done event arrives
And the caller immediately reads the document and its revisions
Then the document version equals the version the event carried
And the revisions list contains the revision the event carried
```

### 6.3 A manual save racing an AI edit on one version leaves exactly one winner
```gherkin
Given a document at a known version
When a manual save and an AI edit apply against that same version concurrently
Then exactly one succeeds
And the other is refused as a conflict
And no content is overwritten without a version increment
```

### 6.4 A worker whose base version no longer matches writes nothing and refunds
```gherkin
Given an edit whose document changed after the edit was queued
When the worker applies its result
Then the edit ends with the version-conflict error code
And no revision and no partial content are written
And the quota charge is refunded
```

### 6.5 A result over the content limit fails the edit rather than truncating
```gherkin
Given an edit whose model result exceeds the maximum document length in code points
When the worker applies it
Then the edit ends in a terminal error
And the document is unchanged
And no truncated content is stored
```
Normalisation precedes measurement, which precedes offset application.

### 6.6 A selection-scoped edit rewrites only the selected range
```gherkin
Given a document containing characters outside the basic plane before the selection
When a selection-scoped edit completes
Then the selected range is replaced
And the remainder of the document is byte-identical
```

### 6.7 Model output is sanitised before it is persisted or streamed
```gherkin
Given an edit whose model output contains a script element, an inline event handler and
  a scripting-scheme link
When the edit completes
Then the stored content carries none of them
And no streamed chunk is rendered as markup by the contract
```
Repeat with upper-case markup under a locale with non-invariant case folding.

---

## 7. History and Quota

### 7.1 A document with no history returns valid empty pages
```gherkin
Given an authenticated user owning a document created before this feature
When they read its revisions and its messages
Then both return an empty page
And neither is an error
```

### 7.2 The first mutation records the pre-edit content as a restorable revision
```gherkin
Given a document with no revision history
When its first AI edit completes
Then the earliest revision holds the content as it was before that edit
And restoring it returns the document to its pre-edit content
```

### 7.3 Restoring a revision creates a new version and destroys nothing
```gherkin
Given an authenticated user owning a document with several revisions
When they restore an earlier revision
Then a new version is created with that revision's content
And the previously current revision is still listed
And restoring the restore is accepted
```

### 7.4 A double-clicked restore creates exactly one new version
```gherkin
Given an authenticated user owning a document with revisions
When two restores of the same revision are submitted concurrently
Then exactly one new version is created
And the other is refused as a conflict
```

### 7.5 List endpoints are bounded, ordered and content-free
```gherkin
Given an authenticated user owning a document with more history than one page holds
When they page through the revisions and the messages
Then the order is stable while new entries are being written
And no page exceeds the server cap even when a larger size is requested
And the revisions list carries no document content
And the query count per page does not grow with the page size
```

### 7.6 The daily quota is enforced, charged once and refunded once
```gherkin
Given an account that has reached its daily edit quota
When it submits another instruction
Then the request is refused as over quota with a reset hint
And the counter never becomes negative
And an edit terminalised twice by cancel and by the reaper is refunded exactly once
```

### 7.7 The quota day boundary follows the configured clock, not the caller's
```gherkin
Given a clock pinned near midnight in a zone other than the canonical one
When an account submits instructions on either side of the canonical day boundary
Then each is counted in the intended day
```

### 7.8 A quota store that cannot be read denies the request
```gherkin
Given a quota store that errors or times out
When an account submits an instruction
Then the request is refused
And no edit is created
```

---
