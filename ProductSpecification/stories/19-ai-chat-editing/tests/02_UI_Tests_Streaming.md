> **Implementation Order**: sections 4-7, continuing `02_UI_Tests.md` — implement after
> submission and freeze work.

# AI chat editing — UI Tests (streaming, terminal handling, revisions)

DSL reference: see the table at the end of `02_UI_Tests.md`.

## 4. Streaming Render

### 4.1 Streamed text appears progressively as plain text
```gherkin
Given an instruction is being processed
When text arrives from the stream
Then it appears progressively in the editor area
And markup in the streamed text is displayed literally, never rendered
```

### 4.2 A dropped stream shows a reconnecting state distinct from a stalled one
```gherkin
Given an instruction is being processed
When the stream connection drops
Then a reconnecting state is shown
And it is visually distinct from the state shown when the stream is merely quiet
When the connection is restored
Then streaming resumes without duplicated text
```

---

## 5. Terminal Handling

### 5.1 A completed edit unfreezes the editor and shows the applied result
```gherkin
Given an instruction is being processed
When the edit completes
Then the editor becomes editable again
And the applied document content is shown
And the assistant reply is appended to the chat
```

### 5.2 A failed edit reverts the buffer and offers a retry
```gherkin
Given an instruction is being processed
When the edit fails
Then an inline error is shown in the chat
And the editor content and version are exactly what they were before the instruction
And a retry is offered
```

### 5.3 Cancelling reverts without presenting a failure
```gherkin
Given an instruction is being processed
When the user cancels it
Then the editor becomes editable again
And the content is exactly what it was before the instruction
And no error message and no retry offer are shown
```

### 5.4 The client timeout releases the editor rather than freezing it forever
```gherkin
Given an instruction is being processed
When no terminal outcome arrives within the client timeout
Then the editor becomes editable again
And the content is reverted
And the user is told the edit did not complete
```

### 5.5 An unrecognised terminal outcome is treated as a failure, not a success
```gherkin
Given an instruction is being processed
When the stream ends with a terminal outcome the client does not recognise
Then the editor is unfrozen
And the content is reverted
And a retry is offered
```

---

## 6. Revisions Panel

### 6.1 Revisions are listed with their number, time and source
```gherkin
Given a document with manual, AI and restore revisions
When the user opens the revisions panel
Then each revision shows its number, its time and its source
```

### 6.2 Restoring asks for confirmation and explains that nothing is destroyed
```gherkin
Given the revisions panel is open
When the user chooses to restore a revision
Then a confirmation explains that a new version will be created
When they confirm
Then the editor shows that revision's content
And a new entry appears at the top of the revisions list
```

### 6.3 A superseded response never overwrites the current view
```gherkin
Given the user restores a revision while an earlier read of the document is still in
  flight
When the earlier response arrives after the restore has rendered
Then the restored content remains displayed
```

---

## 7. Navigation

### 7.1 The revisions panel can be opened and closed from the editor
```gherkin
Given the user is in the editor
When they activate the revisions control
Then the revisions panel is displayed
When they close it
Then the editor and chat panel are displayed again
```

### 7.2 The not-found blocker's link returns to the documents list
```gherkin
Given the not-found blocker is displayed
When the user activates the link back to the documents list
Then the documents list page is displayed
```

Hazard-scan guards continue in `02_UI_Tests_Guards.md`.
