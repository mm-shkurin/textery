> These are additional edge case tests. Implement after core tests pass.

# Authorization — Infrastructure Tests (Extended)

## 1. Clock skew between application instances near a code/lockout expiry boundary

```gherkin
Given two backend instances with slightly different system clocks
When a code or lockout expiry check happens near the boundary on each instance
Then both instances agree on the outcome, using a shared time source (DB clock), not
    each instance's local system time
```
