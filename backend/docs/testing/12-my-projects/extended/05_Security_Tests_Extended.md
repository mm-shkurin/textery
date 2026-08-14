<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Security Tests (Extended)

---

## 1. Credentials

### 1.1 A token for a deleted or disabled account cannot read the feed
```gherkin
Given an access token issued to an account that no longer exists
When the caller lists projects
Then the request is refused as unauthorized
```

### 1.2 A refresh token presented as an access token is refused
```gherkin
Given a refresh token used as the bearer credential
When the caller lists projects
Then the request is refused as unauthorized
```

---

## 2. Input Handling

### 2.1 Control characters in a query cannot forge a log line
```gherkin
Given a search term carrying newline and carriage-return sequences
When the caller searches for it
Then the request produces one log record
And the term appears inside it as a single field
```

### 2.2 An oversized query is rejected before any search runs
```gherkin
Given a search term far beyond the configured maximum
When the caller sends it
Then the request is rejected
And no database work is done
```

### 2.3 Error responses for refused sorts do not enumerate internal column names
```gherkin
Given a sort value that is not accepted
When the caller lists projects
Then the error names the parameter but no database column
```

---

## 3. Enumeration

### 3.1 Paging parameters cannot be used to infer another account's row count
```gherkin
Given two accounts with different numbers of projects
When one caller probes pages beyond its own feed
Then every page is empty
And every response reports only its own total
And nothing indicates another account's items
```

### 3.2 Retry timing does not distinguish absent from foreign
```gherkin
Given a foreign generation id and an unused one
When the caller retries each many times
Then the answers remain indistinguishable
```

### 3.3 Retry cannot be aimed at a document id
```gherkin
Given the id of a document owned by the caller
When the caller retries that id as a generation
Then the request is refused indistinguishably from a missing generation
```

### 3.4 An idempotency key is not echoed back to a caller that did not send it
```gherkin
Given a stored retry record
When any response is returned
Then no idempotency key of any account appears in the response body
```

---

## 4. Rendering

### 4.1 A title carrying right-to-left overrides cannot reorder the card
```gherkin
Given a document whose title carries bidirectional override characters
When the user opens «Мои проекты»
Then the card's own labels stay in place
```

---

## DSL Technical Reference

Inherits `05_Security_Tests.md`.
