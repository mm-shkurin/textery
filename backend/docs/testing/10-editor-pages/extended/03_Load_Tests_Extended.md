<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Editor pages — Load Tests (Extended)

## 1. Save Path Under Rate

### 1.1 Page-settings saves sustain their rate alongside content autosaves
```gherkin
Given the configured throughput baseline
And clients issuing content autosaves and page-settings saves against the same documents
When the load is sustained over the measurement window
Then the save endpoint sustains the target rate
And the conflict rate stays within the expected band for the contention level
And no save is silently dropped
```

Threshold: the project's configured sustained rate; conflict responses are an expected
outcome under contention, not an error — the ceiling applies to failures other than 409.

---

## 2. Mixed Workload

### 2.1 Sustained exports do not starve the interactive save path
```gherkin
Given the configured throughput baseline
And export load running at the render-concurrency bound
When save requests are issued concurrently
Then the save endpoint continues to sustain its target rate
```

Catches the regression where the heavier render path consumes the shared request-thread
budget and turns an export queue into an editor that cannot save.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's declared sustained-rate baseline from `ExpectedLoad.md` |
| `the render-concurrency bound` | Story 17's concurrent-render limit |
| `the expected band for the contention level` | Derived from the number of writers per document in the scenario setup |
