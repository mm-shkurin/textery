> These are additional edge case tests. Implement after core tests pass.

# Authorization — Integration Tests (Extended)

## 1. Multiple concurrent refresh calls with the same refresh token

```gherkin
Given a single valid refresh token
When two refresh requests using that same token are submitted concurrently
Then both succeed with valid access tokens, or the second is rejected cleanly — either
    way, no server error and no token corruption
```
