# AI chat editing — Load Tests

Targets the project's declared **Throughput** profile (`ProductSpecification/ExpectedLoad.md`):
request rate, queue depth and downstream rate-limit compliance — not data volume, not
latency percentiles. This story adds the first long-lived connections in the product, so
concurrent stream count is a throughput concern here rather than a latency one.

---

## 1. Edit submission rate

### 1.1 Edit submission sustains the configured request rate
```gherkin
Given the configured throughput baseline
When instructions are submitted at the target rate over the measurement window
Then every submission is answered as accepted or as a documented refusal
And the error rate stays under the ceiling
And the queue depth stays within its bound
```

Threshold: sustained submission rate over the standard window, queue depth bounded by the
worker concurrency setting. Catches an unbounded queue and a submission path that blocks
on the provider instead of returning immediately.

### 1.2 Provider calls stay within the downstream rate limit under submission load
```gherkin
Given the configured throughput baseline
And the document-edit provider fake configured with the downstream rate limit
When instructions are submitted at the target rate over the measurement window
Then the provider is never called above its rate limit
And edits that cannot be served yet wait in the queue rather than failing
```

Threshold: provider call rate at or under the configured downstream limit. Catches worker
concurrency raised without regard to the provider's limit.

---

## 2. Concurrent streams

### 2.1 Concurrent event streams stay within the connection and pool bounds
```gherkin
Given the configured throughput baseline
When the target number of edit streams are held open simultaneously
Then every stream continues to deliver its events
And checked-out database connections stay within the pool bound
And no stream is served by holding a database connection for its whole lifetime
```

Threshold: concurrent open streams at the configured ceiling; pool checkouts bounded.
Catches the tail-the-events-table implementation that pins one connection per stream —
the failure that turns a hundred edits into a dead pool.

### 2.2 Aborted streams return connections to baseline
```gherkin
Given the target number of edit streams are held open simultaneously
When the clients abort mid-edit
Then open connections return to baseline
And checked-out database connections return to baseline
And the abandoned edits still reach a terminal state
```

Threshold: connection and pool counts return to their pre-test baseline within the
reclaim window. Catches a leak that only appears when clients disappear, which is the
normal case for a browser tab.

---

## 3. Hazard Guards

### 3.1 Steady-state event polling is spread across the interval
```gherkin
Given the configured throughput baseline
When the target number of streams are held open
Then their tail queries are spread across the polling interval
And they do not all query on the same tick
```

Threshold: per-tick query count no greater than the streams divided by the interval, plus
the jitter allowance. Catches every stream polling in lockstep.

### 3.2 Failure paths release their resources as reliably as the success path
```gherkin
Given the configured throughput baseline
When the provider connect-timeout, read-timeout and retry paths are driven repeatedly
Then open sockets, connection-pool checkouts and file descriptors return to baseline
And none of them climbs monotonically across the run
```

Threshold: resource counts return to the pre-test baseline. Catches a client created per
call, and a failure branch that skips the release the success branch performs.

### 3.3 Pathological content does not stall the apply path
```gherkin
Given content at the maximum document length containing deeply nested and
  backtracking-prone markup
When it is normalised, measured, sanitised and applied
Then the work completes within its stated wall-clock bound
```

Threshold: apply-path duration ceiling for worst-case content. Catches a sanitiser or
normaliser whose cost is super-linear in nesting depth.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The load baseline defined in `ProductSpecification/ExpectedLoad.md` |
| `instructions are submitted at the target rate` | POST /api/v1/documents/{id}/ai-edits driven by the load runner |
| `the document-edit provider fake` | The edit-provider port's fake, configured with a call-rate limit |
| `edit streams are held open` | Concurrent GET /ai-edits/{edit_id}/stream connections |
| `the queue depth` | Pending-job count in the edit queue |
| `checked-out database connections` | Connection-pool checkout gauge |
