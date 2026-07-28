> These are additional edge case tests. Implement after core tests pass.

# AI chat editing — UI Tests (Extended)

### 1.1 A very long conversation stays usable
```gherkin
Given a document with a conversation longer than one screen
When the user opens it
Then the newest messages are shown
And earlier messages can be reached by scrolling
```

### 1.2 A long instruction is bounded in the input
```gherkin
Given the user is typing an instruction
When they exceed the maximum length
Then the input shows the limit
And sending is prevented until the instruction fits
```

### 1.3 The attached excerpt survives a failed edit
```gherkin
Given an instruction was sent with an attached excerpt
When the edit fails
Then the excerpt is still attached for the retry
```

### 1.4 The revisions panel reflects a completed edit without a manual refresh
```gherkin
Given the revisions panel is open
When an edit completes
Then the new revision appears in the list
```

### 1.5 Cancelling twice has no additional effect
```gherkin
Given an instruction is being processed
When the user activates cancel twice
Then exactly one cancellation is sent
```

### 1.6 An empty instruction cannot be sent
```gherkin
Given the message input is empty or contains only whitespace
Then the send control is disabled
```
