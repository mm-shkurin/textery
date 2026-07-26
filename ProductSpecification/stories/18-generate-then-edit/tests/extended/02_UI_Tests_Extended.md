> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — UI Tests (Extended)

## 1. Transition Edge Cases

### 1.1 Out-of-order poll responses bind to the latest
```gherkin
Given overlapping completion polls resolve out of order
When the editor opens
Then it reflects the latest poll result, not a stale one
```

### 1.2 A retry after a conversion error succeeds without duplicating
```gherkin
Given a conversion error was shown
When the user retries and it succeeds
Then one document opens in the editor
```

## 2. Editor State

### 2.1 Saving clears the unsaved-state guard
```gherkin
Given a generated document with unsaved edits
When the user saves and then navigates away
Then no unsaved-state warning appears
```
