<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Editor pages — Security Tests (Extended)

## 1. Text Handling

### 1.1 Bidirectional control characters cannot reorder the rendered header
```gherkin
Given a header text containing bidirectional override characters
When the document is displayed and exported
Then the header renders without the surrounding text being visually reordered
```

### 1.2 A header of combining marks cannot expand without bound
```gherkin
Given a header text at the length limit consisting of stacked combining marks
When the document is displayed and exported
Then the render completes within the deadline
And the header stays inside its margin box
```

### 1.3 Normalization cannot be used to slip past the length limit
```gherkin
Given a header text that is within the limit before normalization and over it after
When the caller saves it
Then the request is refused
And the limit is enforced on the normalized form
```

---

## 2. Structural Abuse

### 2.1 Deeply nested content is refused before layout is attempted
```gherkin
Given content nested past the permitted depth
When the caller saves it
Then the request is refused at the boundary
And no layout or render is attempted
```

### 2.2 A document of many empty blocks is refused before layout
```gherkin
Given content consisting of more blocks than permitted, each nearly empty
When the caller saves it
Then the request is refused at the boundary
And the rejection does not depend on rendering the document first
```

---

## 3. Enumeration

### 3.1 Rejection reasons do not disclose whether a document exists
```gherkin
Given a document id owned by another account
When the caller saves invalid page settings against it
Then the response is not found, not a validation error
And the ordering never reveals that the values were checked
```

### 3.2 A conflict response does not disclose another account's state
```gherkin
Given a document owned by another account
When the caller saves under a guessed version
Then the response is not found
And never a conflict, which would confirm the id exists
```
