<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — API Tests (Extended)

---

## 1. Search Edges

### 1.1 A search query of exactly the length bound is accepted
```gherkin
Given a search query of exactly 200 code points
When the caller lists projects
Then the request succeeds
```

### 1.2 Combining diacritics in the query match their precomposed stored form
```gherkin
Given a document whose title is stored in precomposed form
When the caller searches with the same text in decomposed form
Then the document is matched
```

### 1.3 Leading and trailing whitespace in the query is trimmed before matching
```gherkin
Given a document whose title contains a distinctive word
When the caller searches for that word surrounded by spaces
Then the document is matched
```

### 1.4 A whitespace-only query is treated as no query
```gherkin
Given the caller owns projects
When they search for a query of only spaces
Then the full feed is returned
```

### 1.5 A query consisting only of escaped metacharacters matches literally
```gherkin
Given a document whose title contains a percent sign
When the caller searches for a percent sign
Then only documents containing that character are returned
```

### 1.6 Search spans both sources in one query
```gherkin
Given a document and a generation both matching one term
When the caller searches for it
Then both are returned in the same page
```

### 1.7 A term matching a document only through its body still pages correctly
```gherkin
Given more body-only matches than one page holds
When the caller pages through the results
Then every match appears exactly once across the pages
```

---

## 2. Sorting Edges

### 2.1 Sorting by type groups documents and generations of the same type together
```gherkin
Given documents and generations of several document types
When the caller sorts by type
Then items of one type are contiguous regardless of kind
```

### 2.2 Every item is untitled under a title sort
```gherkin
Given the caller owns only untitled documents
When they sort by title
Then the request succeeds and the order is stable across reads
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

### 3.1 A limit of 1 pages the whole feed one item at a time
```gherkin
Given a feed of several projects
When the caller pages through it with a limit of 1
Then every item is returned exactly once, in the requested sort order
```

### 3.2 The minimum and maximum limits are both accepted
```gherkin
Given the caller owns more items than the maximum page holds
When they request the smallest and the largest allowed limit in turn
Then each returns that many items
And a limit of 100 returns exactly 100 items
```

### 3.3 The deepest allowed page answers as fast as the first
```gherkin
Given the caller requests the highest allowed page
When the request is served
Then it completes within the same bound as the first page
```

### 3.4 Repeating an identical list request returns an identical page
```gherkin
Given a feed that is not being written
When the caller repeats the same list request
Then the two responses are identical, including total
```

---

## 4. Preview Edges

### 4.1 The preview of a document shorter than the preview bound is returned whole
```gherkin
Given a document whose content is shorter than the preview bound
When the caller lists projects
Then the preview equals the full content
```

---

## 5. Retry Edges

### 5.1 A retry issued after the source has reached its cap is refused before any write
```gherkin
Given a source generation at its retry cap
When the caller retries it with a fresh idempotency key
Then the request is refused
And no generation row is created
```

### 5.2 A retry of a retry carries the original's parameters
```gherkin
Given a chain of failed generation and failed retry
When the caller retries again
Then the newest generation still carries the original's type, topic, and volume
```

### 5.3 A retry request with a body is answered as if it had none
```gherkin
Given a retry request carrying an arbitrary body
When the caller sends it
Then the created generation matches the source's parameters
```

### 5.4 A retry of a generation that is already a fresh child is refused
```gherkin
Given a generation created moments ago by a retry
When the caller retries that child while it is still running
Then the request is refused as not retryable
```

---

## DSL Technical Reference

Inherits `01_API_Tests.md`.
