<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — Load Tests (Extended)

## 1. Retry Behaviour

### 1.1 Conversion retries back off under sustained failure
```gherkin
Given the configured throughput baseline
And conversions are failing transiently
When clients retry
Then retries back off and are attempt-capped
And do not amplify into a retry storm
```
Threshold: retry arrivals bounded and backed off; no monotonic amplification. Catches an unbounded client retry loop.
