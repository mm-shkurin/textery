> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Load Tests (Extended)

Same throughput profile as the main file.

---

## 1. Mixed Traffic

### 1.1 Search load does not starve the plain feed
```gherkin
Given the configured throughput baseline
When search requests and unfiltered feed requests are issued together
Then the unfiltered feed sustains its target rate
```

Threshold: unfiltered feed holds 200 req/s while search runs concurrently. Catches the
expensive path monopolising the connection pool.

### 1.2 Repeat bursts respect the provider's rate limit
```gherkin
Given the configured throughput baseline
When many accounts repeat failed generations at once
Then calls to the provider stay within its rate limit
And no repeat is silently dropped
```

Threshold: provider call rate under the configured downstream limit. Catches a repeat
path that bypasses the queueing the generation flow already applies.

---

## DSL Technical Reference

Inherits `03_Load_Tests.md`.
