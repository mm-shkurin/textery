# Мои проекты — Load Tests

Throughput profile, per `ProductSpecification/ExpectedLoad.md`: the binding constraint is
request rate, not per-user data volume. This story adds the product's first
typing-frequency endpoint — a debounced search running `ILIKE` over document content — so
the scenarios assert sustained rate and the bounds that keep one expensive query from
holding capacity, not volume scale or latency percentiles.

---

## 1. Feed Reads

### 1.1 The projects feed sustains the expected request rate
```gherkin
Given the configured throughput baseline
And a population of accounts each owning a realistic mix of documents and generations
When the projects feed is requested continuously across those accounts
Then the endpoint sustains the target rate over the window
And the error rate stays under the ceiling
```

Threshold: 200 req/s sustained over 60s, error rate < 0.1%. Catches a merged read whose
cost grows with the feed's second arm — a per-item query behind the union would show up
here as rate collapse, not as a wrong answer.

---

## 2. Search

### 2.1 Search under typing-rate load stays bounded
```gherkin
Given the configured throughput baseline
And accounts whose documents carry content at the maximum stored size
When searches are issued at the rate a debounced input produces across those accounts
Then the endpoint sustains the target rate over the window
And no request exceeds the search timeout without being answered
```

Threshold: 200 req/s sustained over 60s; every request terminal within the search
statement timeout. Catches the unbounded `ILIKE` — an unindexed scan over maximum-size
content that answers correctly at one request per second and collapses at typing rate.

### 2.2 Abandoned searches do not accumulate
```gherkin
Given the configured throughput baseline
When searches are issued and abandoned before they answer, repeatedly
Then the pool's checked-out connections return to their baseline
And no query for an abandoned search is still executing
```

Threshold: checked-out connections return to baseline within one timeout window.
Catches the leak the story names explicitly — discarding a response client-side does not
cancel the server's scan, so a user typing twelve characters holds twelve scans.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|--------------------------|
| `the configured throughput baseline` | The load baseline defined in `ProductSpecification/ExpectedLoad.md` |
| `sustains the target rate over the window` | Throughput counter over the run, asserted against the annotated rate |
| `the search timeout` | `projects_search_statement_timeout_ms` |
| `the pool's checked-out connections` | Connection-pool gauge sampled before and after the run |
| `abandoned before they answer` | Client disconnects before the response |
