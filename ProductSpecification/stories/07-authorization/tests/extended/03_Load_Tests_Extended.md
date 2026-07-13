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
