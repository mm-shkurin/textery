> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Load Tests (Extended)

Same throughput profile as the main file.

---

## 1. Deep pages sustain the rate as well as the first page

```gherkin
Given the configured throughput baseline
And accounts requesting pages near the page bound
When the load runs for the measurement window
Then the sustained rate stays within its threshold
And the error rate stays under its ceiling
```

Threshold: same sustained rate as the first-page scenario. Catches offset scans whose
cost grows with page depth until deep pages dominate the pool.

## 2. Accounts with large histories do not degrade the shared rate

```gherkin
Given the configured throughput baseline
And a minority of accounts holding far more projects than the rest
When the load runs for the measurement window
Then the sustained rate across all accounts stays within its threshold
```

Threshold: rate measured across all accounts, not per account. Catches a query whose
cost scales with one owner's row count and starves unrelated callers.

## 3. Retry bursts do not displace feed reads

```gherkin
Given the configured throughput baseline
And a burst of retries against failed generations
When the load runs for the measurement window
Then the feed's sustained rate stays within its threshold
And retries beyond their cap are refused rather than queued
```

Threshold: feed rate unchanged during the burst. Catches retries consuming the same
pool the reads need.

## 4. Search load does not starve the plain feed

```gherkin
Given the configured throughput baseline
When search requests and unfiltered feed requests are issued together
Then the unfiltered feed sustains its target rate
```

Threshold: unfiltered feed holds 200 req/s while search runs concurrently. Catches the
expensive path monopolising the connection pool.

## 5. Retry bursts respect the provider's rate limit

```gherkin
Given the configured throughput baseline
When many accounts retry failed generations at once
Then calls to the provider stay within its rate limit
And no retry is silently dropped
```

Threshold: provider call rate under the configured downstream limit. Catches a retry
path that bypasses the queueing the generation flow already applies.

---

## DSL Technical Reference

Inherits `03_Load_Tests.md`.
