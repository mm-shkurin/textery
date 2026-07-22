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
