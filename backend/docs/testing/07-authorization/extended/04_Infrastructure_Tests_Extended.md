<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Authorization — Infrastructure Tests (Extended)

## 1. Clock skew between application instances near a code/lockout expiry boundary

```gherkin
Given two backend instances with slightly different system clocks
When a code or lockout expiry check happens near the boundary on each instance
Then both instances agree on the outcome, using a shared time source (DB clock), not
    each instance's local system time
```
