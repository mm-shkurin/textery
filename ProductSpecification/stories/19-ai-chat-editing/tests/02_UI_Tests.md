> **Implementation Order**: sequential TDD — prerequisite guards → panel display →
> interaction → submission and freeze → streaming render → terminal handling →
> revisions panel → navigation.

# AI chat editing — UI Tests

Screens per `19_AiChatEditing.md` and the story's mockups. Client criteria live in
`19_AiChatEditing_Criteria_Client.md`.

## 0. Prerequisite Guards

### 0.1 A document that cannot be loaded blocks the chat panel with a way out
```gherkin
Given the editor is opened for a document that is absent or not the user's
When the page loads
Then a not-found blocker is shown instead of the editor and chat panel
And a link back to the documents list is offered
```

### 0.2 An account over its daily quota cannot type an instruction
```gherkin
Given the user's account has reached its daily edit quota
When they open a document
Then the chat input is disabled
And the reset hint is shown
And the revisions panel remains usable
```

---

## 1. Panel Display

### 1.1 The editor and chat panel render side by side with an empty history
```gherkin
Given the user opens a document that has never been edited by AI
Then the document content is shown in the editor
And the chat panel is shown with its empty state
And the message input is enabled
```

### 1.2 An existing conversation is restored when the document is reopened
```gherkin
Given a document with earlier chat messages
When the user reopens it
Then the earlier messages are shown in order
And the newest message is visible without scrolling
```

### 1.3 The chat history and the revisions panel each show their own load failure
```gherkin
Given the chat history request fails
And the revisions request succeeds
When the user opens the document
Then the chat panel shows a fetch-error state with a retry control
And the revisions panel shows its list normally
```
Assert the mirrored case, and the loading and empty states for each panel.

---

## 2. User Interaction

### 2.1 Selecting text attaches the excerpt to the next instruction
```gherkin
Given the user has opened a document
When they select a passage in the editor
Then the selected excerpt is shown above the message input
And a control to detach it is offered
When they detach it
Then the excerpt is no longer attached
```

---

## 3. Submission and Freeze

### 3.1 Sending an instruction freezes the editor and offers cancellation
```gherkin
Given the user has typed an instruction
When they send it
Then the editor becomes read-only
And an editing indicator is shown
And a cancel control is offered
And the send control is disabled
```

### 3.2 One gesture produces at most one instruction
```gherkin
Given the user has typed an instruction
When they activate the send control twice in rapid succession
Then exactly one instruction is sent
```

### 3.3 A dirty buffer is not silently discarded when an instruction is sent
```gherkin
Given the user has unsaved edits in the editor
When they send an instruction
Then the draft is saved first or the user is asked to confirm
And no unsaved content is lost
```

### 3.4 Leaving with unsaved content is guarded
```gherkin
Given the user has unsaved edits in the editor
When they navigate away or reload
Then a confirmation guard is raised
```

---

Sections 4-7 continue in `02_UI_Tests_Streaming.md`.

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the user opens a document` | Navigate to the editor route for a document id |
| `they send it` | Submit control posts to /ai-edits and opens the event stream |
| `text arrives from the stream` | A chunk event on the SSE connection, read via fetch |
| `the edit completes` | Terminal done event, followed by a re-read of the document |
| `the edit fails` | Terminal error event carrying a stable code |
| `they cancel it` | Cancel control posts to the cancel endpoint |
| `the revisions panel` | Panel backed by GET /revisions |
| `the chat panel` | Panel backed by GET /messages |
