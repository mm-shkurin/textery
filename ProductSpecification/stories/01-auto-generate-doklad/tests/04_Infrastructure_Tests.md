# Auto-generate: доклад — Infrastructure Tests

---

## 1. Database Connection Failure Handling

### 1.1 Generation submission fails cleanly when the database is unavailable

```gherkin
Given the database is unreachable
When a client submits a generation request
Then the request fails with a clear server error
And no partial generation record is left behind
```

---

## 2. Database Recovery After Failure

### 2.1 Pending generations resume processing after the database recovers

```gherkin
Given a generation was created just before the database became unreachable
And the database has since recovered
When the background worker next processes the queue
Then the generation is picked up and processed normally
```

---

## 3. External Service Unavailable Handling

### 3.1 Generation fails gracefully when the generation provider is unreachable

```gherkin
Given the external generation provider is completely unreachable
When the background job attempts to process a generation
Then the generation follows the normal bounded-retry-then-failed policy
And the generation never remains stuck in "pending" or "in_progress"
```

---

## 4. Startup Configuration Validation

### 4.1 The application fails fast at boot when required generation-provider config is missing

```gherkin
Given the generation provider's credential or model configuration is missing
When the application starts up
Then startup fails immediately with a clear configuration error
And the application does not start serving requests in a partially-configured state
```

---

## 5. Reconciliation Sweep Correctness

### 5.1 The reconciliation sweep does not double-process the same stale generation

```gherkin
Given a stale generation is eligible for reconciliation
And the sweep is triggered from more than one backend instance around the same time
When both sweep runs execute
Then only one of them actually transitions the generation
And the generation is not processed twice
```

### 5.2 A generation whose job was silently never enqueued is still reconciled

```gherkin
Given a generation was created but its background job was never actually enqueued
  (the enqueue step itself was lost, not just a worker crash after picking it up)
When enough time has passed with no processing progress
Then the generation is reconciled to "failed" the same way an abandoned in-progress
  generation would be
```

### 5.3 Resource usage returns to baseline after repeated failure and cancellation handling

```gherkin
Given many generations are driven through failure and cancellation paths
  (provider errors, retries, and cancelled hung calls) in sequence
When all of them have finished failing
Then the number of open database connections and provider-call handles returns to
  its baseline level
And none of them are leaked by the failure/cancellation handling
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `the database is unreachable` | Postgres connection refused/timeout injected at the adapter boundary |
| `no partial generation record is left behind` | no committed row for the failed attempt |
| `the background worker next processes the queue` | `arq` worker resumes consuming after DB connectivity is restored |
| `the external generation provider is completely unreachable` | OpenRouter stub returns connection-refused/timeout for every call |
| `credential or model configuration is missing` | `OPENROUTER_API_KEY` or `OPENROUTER_MODEL` env var unset/blank at process start |
| `startup fails immediately` | application process exits non-zero / refuses to bind before serving traffic |
| `the sweep is triggered from more than one backend instance` | two sweep executions run concurrently against the same stale row (simulated multi-instance) |
| `its background job was never actually enqueued` | `Generation` row committed but no corresponding `arq` job was ever created (simulated enqueue loss) |
| `open database connections and provider-call handles` | Postgres active-connection count / HTTP client socket count measured before and after the run |
