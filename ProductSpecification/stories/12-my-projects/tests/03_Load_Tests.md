# Мои проекты — Load Tests

Targets the project's declared **Throughput** profile (`ProductSpecification/ExpectedLoad.md`):
capacity per second under concurrent users, not per-request latency percentiles and not
full-table volume scale. The endpoint's own risk is the unindexed content scan behind `q`
— the question a load test can answer is whether that scan degrades the feed's rate for
everyone, and whether the per-account cap sheds the excess instead of queueing it.

---

## 1. Feed Request Rate

### 1.1 The projects feed sustains its request rate under concurrent users
```gherkin
Given the configured throughput baseline
And concurrent users each paging their own feed
When the feed is requested at the target rate over the measurement window
Then every response is correct for its caller
And the endpoint sustains the target rate for the whole window
And the error rate stays under the ceiling
```

Threshold: sustained target rate over the standard window, error rate under the
configured ceiling. Catches a regression that makes the merge query cost grow per request
— an in-Python merge, a per-row preview read, or a lost `LIMIT` pushdown.

---

## 2. Search Under Concurrency

### 2.1 Concurrent searches do not degrade the unsearched feed's rate
```gherkin
Given the configured throughput baseline
And a share of the concurrent users searching while the rest page normally
When the load runs for the measurement window
Then the unsearched feed sustains its target rate
And the error rate stays under the ceiling
```

Threshold: same sustained rate as 1.1 while searches run concurrently. Catches the
scenario the story names as its scaling risk — unindexed scans holding pooled connections
until unrelated requests queue behind them.

### 2.2 Excess concurrent searches are shed rather than queued
```gherkin
Given the configured throughput baseline
And accounts issuing searches faster than one at a time
When the load runs for the measurement window
Then the excess searches are refused as too many requests
And the connection pool does not saturate
And accepted searches keep completing within the statement deadline
```

Threshold: refusals appear instead of unbounded queueing; pool utilisation stays under
its ceiling. Catches a cap implemented per-process — which bounds nothing across replicas
— and a cap that queues instead of shedding.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The load suite's standard concurrency and seeded accounts (`ExpectedLoad.md`) |
| `the target rate` / `the measurement window` | The suite's configured sustained rate and window |
| `the error rate ceiling` | The suite's configured non-2xx share |
| `refused as too many requests` | 429 `SEARCH_BUSY` |
| `the statement deadline` | 3 s, `SET LOCAL` per request |
