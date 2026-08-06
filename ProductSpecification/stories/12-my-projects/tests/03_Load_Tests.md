# Мои проекты — Load Tests

Targets the project's declared **Throughput** profile (`ProductSpecification/ExpectedLoad.md`):
capacity per second under concurrent users, not per-request latency percentiles and not
full-table volume scale. This story adds the product's first typing-frequency endpoint —
a debounced search running `ILIKE` over document content — so the scenarios assert
sustained rate and the bounds that keep one expensive query from holding capacity.

---

## 1. Feed Request Rate

### 1.1 The projects feed sustains its request rate under concurrent users
```gherkin
Given the configured throughput baseline
And concurrent users each owning a realistic mix of documents and generations
And each of them paging their own feed
When the feed is requested at the target rate over the measurement window
Then every response is correct for its caller
And the endpoint sustains the target rate for the whole window
And the error rate stays under the ceiling
```

Threshold: 200 req/s sustained over 60 s, error rate < 0.1%. Catches a regression that
makes the merge query cost grow per request — an in-Python merge, a per-row preview read,
a lost `LIMIT` pushdown, or a per-item query behind the union. All of them show up here as
rate collapse, not as a wrong answer.

---

## 2. Search Under Concurrency

### 2.1 Concurrent searches do not degrade the unsearched feed's rate
```gherkin
Given the configured throughput baseline
And accounts whose documents carry content at the maximum stored size
And a share of the concurrent users searching at the rate a debounced input produces
And the rest paging normally
When the load runs for the measurement window
Then the unsearched feed sustains its target rate
And the error rate stays under the ceiling
And no request exceeds the statement deadline without being answered
```

Threshold: same 200 req/s sustained rate as 1.1 while searches run concurrently; every
request terminal within the statement deadline. Catches the scenario the story names as
its scaling risk — unindexed scans over maximum-size content holding pooled connections
until unrelated requests queue behind them, correct at one request per second and
collapsing at typing rate.

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

### 2.3 Abandoned searches do not accumulate
```gherkin
Given the configured throughput baseline
When searches are issued and abandoned before they answer, repeatedly
Then the pool's checked-out connections return to their baseline
And no query for an abandoned search is still executing
```

Threshold: checked-out connections return to baseline within one deadline window.
Catches the leak the story names explicitly — discarding a response client-side does not
cancel the server's scan, so a user typing twelve characters holds twelve scans.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The load suite's standard concurrency and seeded accounts (`ExpectedLoad.md`) |
| `the target rate` / `the measurement window` | The suite's configured sustained rate and window (200 req/s over 60 s) |
| `sustains the target rate over the window` | Throughput counter over the run, asserted against the annotated rate |
| `the error rate ceiling` | The suite's configured non-2xx share (< 0.1%) |
| `refused as too many requests` | 429 `SEARCH_BUSY` |
| `the statement deadline` | 3 s, `SET LOCAL` per request |
| `the pool's checked-out connections` | Connection-pool gauge sampled before and after the run |
| `abandoned before they answer` | Client disconnects before the response |
