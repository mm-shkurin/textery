> **Implementation Order**: hazard-scan guards folded in from the catalogue fan-out.
> Each closes a fired trigger no other scenario would go red on. Implement alongside the
> section each references.

# AI chat editing — UI Tests (hazard guards)

DSL reference: see the table at the end of `02_UI_Tests.md`.

---

## 8. Hazard Guards


Folded in from the hazard-catalogue scan — each closes a fired trigger that no other
scenario would go red on.

### 8.1 Selection offsets are sent as code points, not as editor indices
```gherkin
Given a document containing a character outside the basic plane before the passage the
  user selects
When the user selects that passage and sends an instruction
Then the offsets sent are the code-point offsets of the selection
And they differ from the editor's own index values for the same selection
And the edit rewrites exactly the selected passage
```
A fixture where the two representations coincide does not exercise this.

### 8.2 A retry after a lost response does not create a second edit
```gherkin
Given an instruction was sent and its response was lost in transit
When the client retries it unchanged
Then exactly one edit and one chat message exist on the server
```

### 8.3 An edited retry carries a new key and is actually executed
```gherkin
Given an instruction failed and the retry offer is shown
When the user changes the instruction text and retries
Then a new idempotency key is sent
And the new instruction is executed rather than refused as a mismatch
```

### 8.4 The client timeout releases the server edit, not only the editor
```gherkin
Given an instruction is being processed
When no terminal outcome arrives within the client timeout
Then the client cancels the edit on the server
And no revision and no version change land afterwards
```
Without this the user is told the edit failed and their buffer is reverted while the
worker still commits a new version behind them.

### 8.5 A stale or post-terminal event is ignored
```gherkin
Given a client reading an edit's stream
When an event arrives with a sequence number lower than one already rendered
And a chunk arrives after the terminal event
Then neither changes what is displayed
```

### 8.6 An unrecognised non-terminal event does not break the stream
```gherkin
Given a client reading an edit's stream
When an event of a type the client does not recognise arrives between chunks
Then it is ignored
And subsequent chunks and the terminal event are still handled
```

### 8.7 A failed re-fetch after completion never leaves unsanitised text on screen
```gherkin
Given an instruction completed successfully
When the follow-up read of the document fails
Then the editor is unfrozen
And the user is told the edit applied but could not be reloaded, with a retry
And the streamed plain text is not left presented as the applied document
```

### 8.8 The document load has a loading state and a distinct failure state
```gherkin
Given the editor is opening a document
Then a loading state is shown while the request is in flight
When the request fails with a server or network error
Then an error state with a retry is shown
And it is visually distinct from the not-found blocker
```

### 8.9 A failed restore leaves the pre-restore content in place
```gherkin
Given the user confirms a restore
When the restore request fails
Then an error is shown
And the editor still shows the content it had before the restore
```

### 8.10 Restoring cannot be double-submitted
```gherkin
Given the restore confirmation is shown
When the user confirms twice in rapid succession
Then exactly one restore is sent
And exactly one new revision appears
```

### 8.11 A session expiring with unsaved content does not discard it
```gherkin
Given the user has unsaved edits in the editor
When the next request is refused as unauthenticated
Then the unsaved content is preserved across re-authentication
And it is not discarded by the redirect
```

### 8.12 Revision times are shown in the intended day
```gherkin
Given a revision recorded near midnight in a zone other than the display zone
And a clock under test control
When the revisions panel is opened
Then the revision is shown in its intended local day
```

### 8.13 Stream reconnection backs off rather than retrying in a tight loop
```gherkin
Given a client whose stream connection drops repeatedly
When it reconnects
Then successive attempts are spaced with growing, jittered delays
And attempts stop at the configured cap
```
