<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Authorization — Integration Tests (Extended)

## 1. Multiple concurrent refresh calls with the same refresh token

```gherkin
Given a single valid refresh token
When two refresh requests using that same token are submitted concurrently
Then both succeed with valid access tokens, or the second is rejected cleanly — either
    way, no server error and no token corruption
```
