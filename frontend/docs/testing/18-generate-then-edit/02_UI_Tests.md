<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/02_UI_Tests.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the flow change (mode modal gone), then the auto-transition, then the
> non-happy async states, then the unsaved-state guard.

# Generate → edit — UI Tests

Selenium against the real stack. The editor surface is story-5's; this story adds the
auto-open-from-generation path and removes the mode-select modal.

---

## 1. Flow Display

### 1.1 Selecting a type goes straight to generation
```gherkin
Given the user is on the create flow
When they pick a document type
Then generation starts immediately
And no mode-select modal is shown
```

### 1.2 A generating document shows progress
```gherkin
Given the user has started a generation
When the result is not ready yet
Then a generating state is shown
```

---

## 2. Auto-Transition to Editor

### 2.1 A completed generation opens automatically in the editor
```gherkin
Given the user is watching a generation complete
When the text becomes ready
Then the surface becomes the editor with the generated content loaded
And the user made no extra click to get there
```

### 2.2 The auto-transition fires the conversion exactly once
```gherkin
Given a generation that completes
When two poll responses both observe completion before the first conversion returns
Then exactly one conversion request is sent
```

### 2.3 The editor is populated from the conversion response, not a re-read
```gherkin
Given a conversion has just succeeded
And the document read path is made to serve a stale result
When the editor opens
Then it shows the just-converted content from the conversion response
And not a stale re-read
```

---

## 3. Editing

### 3.1 The generated document is editable and saves
```gherkin
Given a generated document open in the editor
When the user edits the text and saves
Then the save succeeds like a manual document
```

---

## 4. Non-Happy Async States

### 4.1 A failed generation shows a distinct error, not a perpetual spinner
```gherkin
Given the user has started a generation
When the generation resolves as failed
Then a failure state with a retry is shown
And it is visually distinct from the generating state
```

### 4.2 A conversion error keeps the text and offers retry
```gherkin
Given a generation has completed
When the conversion request fails
Then an inline error is shown
And the generated text remains visible
And the user can retry without losing it
```

### 4.3 A transient poll error shows a distinct error, not a spinner
```gherkin
Given the user is watching a generation
When a poll request fails transiently
Then an error with a retry is shown
And it is distinct from the generating state
```

### 4.4 A generation that never finishes stops at the client deadline
```gherkin
Given the user is watching a generation
When the generation never reaches a terminal state past the client deadline
Then the generating state is left for an error or retry state
And the client does not spin forever
```

---

## 5. Unsaved-State Protection

### 5.1 Leaving with unsaved edits is guarded
```gherkin
Given a generated document open with unsaved edits
When the user attempts to navigate away or refresh
Then they are warned before the edits are discarded
```

---

## 6. Secondary Entry & Navigation

### 6.1 A blank document can still be started from scratch
```gherkin
Given the user is on the create flow
When they choose to start from a blank page
Then an empty editor opens with no generation
```

### 6.2 The converted document appears in history
```gherkin
Given the user has converted a generation and saved it
When they open their history
Then the document is listed
And no duplicate generation-plus-document pair is shown
```
