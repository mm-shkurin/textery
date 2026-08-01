> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Security Tests (Extended)

---

## 1. Input Handling

### 1.1 Control characters in a query cannot forge a log line
```gherkin
Given a search term carrying newline and carriage-return sequences
When the caller searches for it
Then the request produces one log record
And the term appears inside it as a single field
```

### 1.2 An oversized query is rejected before any search runs
```gherkin
Given a search term far beyond the configured maximum
When the caller sends it
Then the request is rejected
And no database work is done
```

---

## 2. Enumeration

### 2.1 Paging cannot reveal that other work exists
```gherkin
Given two accounts owning projects
When one pages far beyond their own results
Then every page is empty
And nothing indicates another account's items
```

### 2.2 Repeat timing does not distinguish absent from foreign
```gherkin
Given a foreign generation id and an unused one
When the caller repeats each many times
Then the answers remain indistinguishable
```

---

## 3. Rendering

### 3.1 A title carrying right-to-left overrides cannot reorder the card
```gherkin
Given a document whose title carries bidirectional override characters
When the user opens «Мои проекты»
Then the card's own labels stay in place
```

---

## DSL Technical Reference

Inherits `05_Security_Tests.md`.
