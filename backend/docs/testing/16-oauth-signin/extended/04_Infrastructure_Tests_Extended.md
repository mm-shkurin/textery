<!-- COPIED FILE. Source of truth: ProductSpecification/stories/16-oauth-signin/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# OAuth sign-in — Infrastructure Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Store recovery

### 1.1 Exchange recovers after the handoff-code store comes back

```gherkin
Given the handoff-code store was briefly unavailable and has recovered
When a freshly minted handoff code is exchanged
Then the exchange succeeds
```
