> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — API Tests (Extended)

---

## 1. Search Edges

### 1.1 A whitespace-only query is treated as no query
```gherkin
Given the caller owns projects
When they search for a query of only spaces
Then the full feed is returned
```

### 1.2 Search spans both sources in one query
```gherkin
Given a document and a generation both matching one term
When the caller searches for it
Then both are returned in the same page
```

### 1.3 A term matching a document only through its body still pages correctly
```gherkin
Given more body-only matches than one page holds
When the caller pages through the results
Then every match appears exactly once across the pages
```

---

## 2. Sorting Edges

### 2.1 Every item is untitled under a title sort
```gherkin
Given the caller owns only untitled documents
When they sort by title
Then the request succeeds and the order is stable across reads
```

### 2.2 Type ordering places both sources together
```gherkin
Given documents and generations sharing a type
When the caller sorts by type
Then items of the same type are adjacent regardless of source
```

### 2.3 Updated ordering reflects an edit
```gherkin
Given two documents created in a known order
When the older one is edited
And the caller sorts by last change
Then the edited one comes first
```

---

## 3. Paging Edges

### 3.1 The minimum and maximum limits are both accepted
```gherkin
Given the caller owns more items than the maximum page holds
When they request the smallest and the largest allowed limit in turn
Then each returns that many items
```

### 3.2 The deepest allowed page answers as fast as the first
```gherkin
Given the caller requests the highest allowed page
When the request is served
Then it completes within the same bound as the first page
```

---

## 4. Repeat Edges

### 4.1 A repeat of a repeat carries the original's parameters
```gherkin
Given a chain of failed generation and failed repeat
When the caller repeats again
Then the newest generation still carries the original's type, topic, and volume
```

### 4.2 A repeat request with a body is answered as if it had none
```gherkin
Given a repeat request carrying an arbitrary body
When the caller sends it
Then the created generation matches the source's parameters
```

### 4.3 A repeat of a generation that is already a fresh child is refused
```gherkin
Given a generation created moments ago by a repeat
When the caller repeats that child while it is still running
Then the request is refused as not repeatable
```

---

## DSL Technical Reference

Inherits `01_API_Tests.md`.
