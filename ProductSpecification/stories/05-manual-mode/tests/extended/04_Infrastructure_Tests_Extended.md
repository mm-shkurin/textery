> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — Infrastructure Tests (Extended)

## 1. Resource Cleanup

### 1.1 Repeated failed saves do not leak database connections

```gherkin
Given many save requests fail in sequence due to a transient database error
When all of them have finished failing
Then the number of open database connections returns to its baseline level
```
