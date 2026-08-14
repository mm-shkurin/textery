<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/06_Integration_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — Integration Tests

> **Implementation Order**: 1.x proves the prompt reaches GigaChat intact; 2.x proves the
> hand-off did not disturb the failure handling story 1 built.

---

## 1. Provider Success Path

### 1.1 The реферат prompt reaches the provider

```gherkin
Given the provider stub records what it receives
When a реферат generation is dispatched
Then the provider received the реферат structural instructions
And it received the user's topic
```

### 1.2 The provider's document becomes the generation's content

```gherkin
Given the provider stub returns a document
When a реферат generation is dispatched and completes
Then the generation's content is that document
And the generation is recorded as a реферат
```

---

## 2. Provider Failure Modes

### 2.1 A provider error still ends the generation as failed

```gherkin
Given the provider stub returns an error status
When a реферат generation is dispatched
Then the generation ends as failed after the retry budget is spent
And it is never left pending
```

### 2.2 A provider timeout still ends the generation as failed

```gherkin
Given the provider stub does not respond within the call timeout
When a реферат generation is dispatched
Then the generation ends as failed
And the in-flight call is not left running
```

### 2.3 A malformed provider body still ends the generation as failed

```gherkin
Given the provider stub returns a body the client cannot read as a completion
When a реферат generation is dispatched
Then the generation ends as failed
And the failure category is recorded server-side
```

2.1–2.3 assert story 1's behaviour on story 4's path. They exist because the refactor
edits the one method the retry and timeout logic wraps: a behaviour change hidden inside
a "mechanical" move would surface as a stuck or silently-succeeding generation, not as a
prompt bug.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the provider stub` | GigaChat stub server — never the live API |
| `a реферат generation is dispatched` | Worker processes a `Generation` with `document_type="реферат"` |
| `the реферат structural instructions` | введение / разделы / заключение directives plus the bibliography ban |
| `the retry budget` | Bounded retries with jittered backoff, per story 1 |
| `the failure category` | Server-side distinguishable category (timeout / malformed / error status), client still sees a bare `failed` |
