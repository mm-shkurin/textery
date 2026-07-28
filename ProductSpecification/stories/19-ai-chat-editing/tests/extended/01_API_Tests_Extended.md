> These are additional edge case tests. Implement after core tests pass.

# AI chat editing — API Tests (Extended)

## 1. Instruction and selection edges

### 1.1 A selection covering the whole document behaves like a whole-document edit
```gherkin
Given an authenticated user owning a document
When they submit an instruction selecting the entire content
Then the edit completes
And the result replaces the whole document
```

### 1.2 A selection at the very start and at the very end is accepted
```gherkin
Given an authenticated user owning a document
When they submit an instruction selecting the first character
And they submit one selecting the last character
Then both are accepted
```

### 1.3 An instruction containing only formatting characters is treated as blank
```gherkin
Given an authenticated user owning a document
When they submit an instruction consisting solely of zero-width and formatting characters
Then the request is refused
```

---

## 2. History paging edges

### 2.1 A cursor from a different document is rejected
```gherkin
Given an authenticated user owning two documents with history
When they page the second document's revisions using a cursor from the first
Then the request is refused
```

### 2.2 Paging remains stable when entries are added mid-walk
```gherkin
Given an authenticated user paging through revisions
When new revisions are recorded between page requests
Then no already-seen entry is repeated
And no pre-existing entry is skipped
```

### 2.3 The last page reports that it is the last
```gherkin
Given a document whose history fits in fewer entries than the page size
When the user reads the first page
Then no further cursor is offered
```

---

## 3. Restore edges

### 3.1 Restoring the current content is accepted and still creates a version
```gherkin
Given a document whose latest revision matches its current content
When the user restores that revision
Then a new version is created
And the content is unchanged
```

### 3.2 A restore chain remains fully restorable
```gherkin
Given a document restored twice in a row
When the user restores the revision recorded before the first restore
Then the content matches that revision
And every intermediate revision is still listed
```

---

## 4. Streaming edges

### 4.1 An edit with no chunks still terminates
```gherkin
Given an edit whose provider returns its whole result at once
When a client reads the stream
Then a terminal event is delivered
And the stream closes
```

### 4.2 A very long tail is replayed in bounded batches
```gherkin
Given an edit with far more events than one batch holds
When a client reconnects from the first event
Then all events are delivered in order
And no single response materialises the whole tail
```
