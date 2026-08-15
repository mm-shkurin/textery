<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Authorization — Load Tests (Extended)

## 1. Verify-code endpoint under concurrent load for the same account

```gherkin
Given the configured throughput baseline
And repeated concurrent verify requests against the same pending account
When the mix is sustained over the baseline window
Then exactly one verification transition occurs, no error-rate spike from the
    concurrency itself
```
