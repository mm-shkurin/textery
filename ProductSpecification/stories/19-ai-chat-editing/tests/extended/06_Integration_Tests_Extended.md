> These are additional edge case tests. Implement after core tests pass.

# AI chat editing — Integration Tests (Extended)

### 1.1 The provider receives the document, the selection and the recent conversation
```gherkin
Given a document with an earlier conversation
When an edit is executed with a selection attached
Then the provider request carries the document content, the selected range and the most
  recent messages
And it carries no message from another document
```

### 1.2 A provider response longer than the document limit is rejected before persisting
```gherkin
Given a provider that returns more content than the document limit allows
When the edit is executed
Then the edit ends in a terminal error
And nothing is written to the document
```

### 1.3 A provider that streams slowly still finishes within the deadline
```gherkin
Given a provider that emits its parts slowly but within the deadline
When the edit is executed
Then it completes normally
And the events arrive progressively rather than all at the end
```

### 1.4 A provider that exceeds the deadline is abandoned
```gherkin
Given a provider that emits parts past the edit deadline
When the edit is executed
Then the edit ends terminal at the deadline
And later parts are not applied
```
