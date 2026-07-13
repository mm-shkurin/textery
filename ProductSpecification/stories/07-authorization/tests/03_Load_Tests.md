# Authorization — Load Tests

This story's load tests target the **Throughput** profile declared in
`ProductSpecification/ExpectedLoad.md` (hundreds of concurrent users; capacity-per-second
is the binding constraint). Login/register are otherwise one-shot per-user actions, but
the hazard-scan (group 6) flagged that lockout-counter and verification-code writes share
the DB connection pool with the rest of the backend under concurrent load — that shared
resource is the risk this file exercises, not per-request latency.

---

## 1. Concurrent Auth Traffic — Connection Pool

### 1.1 Sustained concurrent login/register traffic stays within the connection pool budget

```gherkin
Given the configured throughput baseline
And a mix of concurrent registration, verify, and login requests, including failure
    branches (locked-out login, expired-code verify, duplicate-email register)
When the mix is sustained over the baseline window
Then all requests complete without connection-pool exhaustion errors
And the pool's active-connection count returns to baseline after the window ends
```

Threshold: pool utilization stays under its configured limit throughout; active
connections return to baseline within one polling interval after load stops. Catches a
connection leak in the lockout-counter or verification-code write paths.

### 1.2 Requests beyond pool capacity get a bounded wait or an explicit reject, never an unhandled hang

```gherkin
Given the configured throughput baseline
And auth traffic driven past the connection pool's configured capacity
When requests exceed that capacity
Then each excess request either waits up to a bounded timeout and then proceeds, or is
    explicitly rejected with a 5xx
And no request hangs indefinitely or crashes the worker
```

Threshold: excess requests resolve (success or explicit reject) within the configured
pool-acquire timeout; none exceed it silently. Catches an undefined exhaustion behavior
that would otherwise surface as a hang or crash in production.

---

## 2. Concurrent Auth Traffic — Sustained Rate

### 2.1 Login endpoint sustains the configured request rate

```gherkin
Given the configured throughput baseline
When login requests are sustained at the baseline rate over the baseline window
Then the error rate stays within the configured ceiling
And the endpoint sustains the baseline request rate for the full window
```

Threshold: sustains the configured req/s baseline over the window with error rate under
the configured ceiling. Catches regressions in the atomic lockout-counter update path
(e.g., a lock contention hot spot) that would degrade throughput under concurrency.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|---------------------------|
| `the configured throughput baseline` | Per `ExpectedLoad.md` — hundreds of concurrent users; exact req/s and window values set at load-scenario implementation time against the provisioned load-test environment |
| `connection-pool exhaustion errors` | DB pool acquire timeout/rejection surfaced as a 5xx, not silently retried forever |
| `active-connection count returns to baseline` | Pool metrics sampled before, during, and after the load window |
