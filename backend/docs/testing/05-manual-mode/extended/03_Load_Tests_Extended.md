<!-- COPIED FILE. Source of truth: ProductSpecification/stories/05-manual-mode/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — Load Tests (Extended)

## 1. Recovery After a Load Spike

### 1.1 Throughput recovers after a burst subsides

```gherkin
Given the create/save endpoints have just handled a burst above the configured
  throughput baseline
When the burst subsides back to the baseline rate
Then the endpoints return to the baseline error rate within the recovery window
```
