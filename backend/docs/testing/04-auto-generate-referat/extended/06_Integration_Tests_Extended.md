<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — Integration Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Re-delivery

### 1.1 A redelivered job does not generate twice

```gherkin
Given a реферат generation that already completed
When its job is delivered again
Then the provider is not called a second time
And the stored content is unchanged
```

Story 1 established the compare-and-swap guard on status transitions. This asserts it
still holds for a реферат, where the only difference is which template built the prompt.

### 1.2 A generation abandoned mid-flight is swept to failed

```gherkin
Given a реферат generation left in progress past the staleness window
When the reconciliation runs
Then the generation ends as failed
```

---

## 2. Extended Failure Surface

### 2.1 A provider rate-limit response is distinguishable from other failures

```gherkin
Given the provider stub responds with a rate-limit status
When a реферат generation is dispatched
Then the recorded failure category names the rate limit
And the client still sees a bare failed status
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `its job is delivered again` | Same job re-enqueued / redelivered to a worker |
| `the staleness window` | Story 1's reconciliation threshold for pending / in-progress rows |
| `the recorded failure category` | Server-side category field, not the client-facing `status` |
