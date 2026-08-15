<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — Security Tests (Extended)

## 1. Injection Variants

### 1.1 Nested and encoded markup does not survive sanitization
```gherkin
Given a generation whose content nests markup inside markdown and uses HTML entity encoding
When it is converted
Then no executable markup survives in stored or rendered content
```

## 2. Idempotency Abuse

### 2.1 A replayed key from another account does not disclose the document
```gherkin
Given a document converted by one account with an idempotency key
When another account sends the same key
Then it does not receive the first account's document
```
