> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Integration Tests (Extended)

---

## 1. Provider Behaviour

### 1.1 A provider rate-limit answer marks the repeat failed, not lost
```gherkin
Given the provider refuses with a rate-limit answer
When the caller repeats a failed generation
Then the new generation ends as failed
And the feed offers to repeat it again
```

### 1.2 A provider answer in an unexpected shape fails closed
```gherkin
Given the provider answers with content the flow cannot parse
When the caller repeats a failed generation
Then the generation ends as failed
And nothing unparsed is stored
```

---

## 2. Cross-Flow

### 2.1 A repeat that completes can be converted like any generation
```gherkin
Given a repeat that completed
When it is converted into a document
Then the document appears in the feed in place of the generation
```

### 2.2 Deprecated list endpoints keep answering while the feed is used
```gherkin
Given the projects feed is in use
When the older document and generation list endpoints are called
Then both still answer as their contracts describe
```

---

## DSL Technical Reference

Inherits `06_Integration_Tests.md`.
