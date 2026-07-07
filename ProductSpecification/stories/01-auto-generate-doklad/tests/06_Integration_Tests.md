# Auto-generate: доклад — Integration Tests

Covers the worker ↔ external generation-provider integration (arq job → OpenRouter →
Document/status), including the outbound half of the idempotency guarantee from
`01_API_Tests.md` section 3 — re-run safety is mandatory in both files whenever an
external system is involved.

---

## 1. Generation Provider — Success Flow

### 1.1 A successful provider call produces a completed document

```gherkin
Given a pending generation is processed by the background worker
And the generation provider returns a successful result
Then a document is created with the generated content
And the generation's status becomes "completed"
```

### 1.2 The requested volume converts to a pinned, tested prompt budget for Cyrillic text

```gherkin
Given a pending generation for the minimum supported volume, with Cyrillic-heavy
  topic and requirements
And a pending generation for the maximum supported volume, with the same kind of
  Cyrillic-heavy content
When each is processed by the background worker
Then the prompt/budget sent to the generation provider matches the pinned conversion
  constant's expected value for that volume
And the conversion is not silently assumed to behave the same as it would for
  Latin-script text
```

---

## 2. Generation Provider — Error Handling

### 2.1 Permanent and transient provider errors are handled differently

```gherkin
Given a pending generation whose provider call is rejected as permanently invalid
When the background worker processes it
Then the generation fails immediately without consuming its retry budget

Given a pending generation whose provider call fails with a transient server error
When the background worker processes it
Then the attempt is retried according to the bounded retry policy
```

### 2.2 A malformed or empty provider response is treated as a failure

```gherkin
Given a pending generation whose provider call returns an empty or malformed result
When the background worker processes it
Then the generation is treated as failed, not as a silent success with empty content
```

### 2.3 Each failure family is recorded with a distinguishable category server-side

```gherkin
Given generations that fail for different reasons — a rate-limit response, a content-policy
  rejection, a timeout, and a malformed response
When each is processed by the background worker
Then each failure is persisted or logged with a category that distinguishes it from
  the others
And the client-facing status remains a bare "failed" for all of them regardless
```

---

## 3. Generation Provider — Timeout Handling

### 3.1 A hung provider call is cancelled at the job deadline

```gherkin
Given a pending generation whose provider call never returns
When the job's deadline is reached
Then the in-flight call is cancelled rather than left running
And the generation resolves to "failed"
```

---

## 4. Job Redelivery — Idempotency (outbound half)

### 4.1 Redelivering the same background job does not call the provider twice

```gherkin
Given a background job for a generation has already completed its provider call
  and committed its result
When the same job is redelivered to the worker
Then the provider is not called again for that generation
And no second document is created
```

### 4.2 Redelivering a job for an already-failed generation does not reprocess it

```gherkin
Given a background job for a generation has already exhausted its retries and reached
  "failed"
When the same job is redelivered to the worker
Then the provider is not called again for that generation
And the generation's status remains "failed", not silently reset or reprocessed
```

---

## 5. Transaction Atomicity

### 5.1 The document and the completed status commit together, never one without the other

```gherkin
Given a generation whose provider call has already succeeded
When the commit of the resulting document and the status update is interrupted partway
Then no orphan document exists for a generation that isn't marked "completed"
And no generation is marked "completed" without its document present
```

### 5.2 A commit failure after a successful provider call does not trigger a duplicate call

```gherkin
Given a generation whose provider call succeeded but whose result failed to commit
When the generation is retried
Then the generation provider is not called again to reproduce a result that was
  already obtained but lost on commit, unless the system explicitly re-attempts by design
And the generation reaches a final, correct state rather than duplicating provider spend
```

---

## 6. Deadline Budget Composition

### 6.1 The bounded retry sequence fits within the job's overall deadline

```gherkin
Given a generation whose provider calls repeatedly time out, driving the full bounded
  retry sequence with backoff
When the total time spent across all attempts approaches the job's overall deadline
Then the job still aborts cleanly within its own deadline
And no attempt is left running past that deadline
```

---

## 7. Failure Isolation

### 7.1 A permanently failing generation does not block other generations from completing

```gherkin
Given one generation whose provider call always fails permanently
And a different, valid generation is queued around the same time
When both are processed
Then the valid generation still completes successfully
And the permanently-failing generation does not consume capacity needed by the valid one
```

---

## 8. Retry Timing Spread

### 8.1 Concurrent retries after a shared transient outage do not all retry at the same instant

```gherkin
Given several generations fail at the same time due to a shared transient provider outage
When each one's retry fires
Then their retry attempts are spread out rather than landing on the same instant
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `processed by the background worker` | `arq` job dequeued, worker calls the OpenRouter client port |
| `returns a successful result` | stub OpenRouter server responds 200 with generated text |
| `rejected as permanently invalid` | stub OpenRouter server responds 4xx |
| `fails with a transient server error` | stub OpenRouter server responds 5xx or times out |
| `consuming its retry budget` | retry counter/backoff state associated with the generation's job |
| `empty or malformed result` | stub OpenRouter server responds 200 with an empty/unparseable body |
| `never returns` | stub OpenRouter server holds the connection open past the job's configured deadline |
| `cancelled rather than left running` | the HTTP client call is aborted, not merely timed-out client-side while still running server-side |
| `already completed its provider call and committed its result` | `Generation.status = completed`, `Document` row exists |
| `the same job is redelivered` | same `arq` job id/payload re-dequeued (simulated redelivery) |
| `the minimum / maximum supported volume` | `volume_pages: 1` / `volume_pages: 10` |
| `the pinned conversion constant's expected value` | the documented pages→token/char budget formula, asserted against the actual prompt/request sent to the stub OpenRouter server |
| `a rate-limit response, a content-policy rejection, a timeout, and a malformed response` | stub OpenRouter server configured to return each distinct failure shape per sub-scenario |
| `persisted or logged with a category that distinguishes it` | a failure-category field/log attribute distinct from the bare `status` value |
| `already exhausted its retries and reached "failed"` | `Generation.status = failed` via the retry-exhaustion path, prior to redelivery |
| `the commit of the resulting document and the status update is interrupted partway` | fault injected between the `Document` insert and the `Generation` status write in the same unit of work |
| `whose result failed to commit` | provider call returns 200, then the DB write raises/aborts before commit |
| `the total time spent across all attempts approaches the job's overall deadline` | per-call timeout × configured retry count × backoff summed close to the `arq` job timeout |
| `a different, valid generation is queued around the same time` | a second, independent `Generation`/job submitted concurrently with the permanently-failing one |
| `does not consume capacity needed by the valid one` | worker/`max_jobs` slot released after the permanent failure, not held for the full retry budget |
| `their retry attempts are spread out` | retry timestamps checked for jitter/variance, not a single synchronized instant |
