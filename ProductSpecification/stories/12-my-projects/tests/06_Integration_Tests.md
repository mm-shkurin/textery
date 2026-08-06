# Мои проекты — Integration Tests

Covers the two seams this story adds outside its own request handler: «Повторить» →
background job queue → worker (the outbound half of the idempotency guarantee asserted
inbound in `01_API_Tests.md` section 8), and the retry path running beside the existing
stale-generation sweep, which writes the same rows continuously.

---

## 1. Retry → Job Queue

### 1.1 An accepted retry enqueues exactly one job for the new generation

```gherkin
Given a failed generation belonging to the caller
When the caller retries it
Then one background job is enqueued
And the job names the new generation, not the failed source
```

### 1.2 A replayed retry key enqueues no second job

```gherkin
Given a retry that was already accepted with an idempotency key
When the same key is replayed against the same source
Then the stored generation is returned
And no additional background job is enqueued
```

### 1.3 A retry whose enqueue fails leaves no generation the worker will never pick up

```gherkin
Given a failed generation belonging to the caller
And the job queue is unavailable
When the caller retries it
Then the request fails
And no generation is left in a non-terminal status with no job behind it
```

### 1.4 A retry that stored its generation but lost the response is not enqueued twice

```gherkin
Given a retry whose generation and job were both created
And the caller never received the response
When the caller repeats the request with the same idempotency key
Then the stored generation is returned
And the job count for that generation is still one
```

### 1.5 The enqueued job carries the source's stored parameters, not client input

```gherkin
Given a failed generation created with a specific topic, type and volume
When the caller retries it
Then the enqueued job carries exactly those stored parameters
And nothing from the retry request influences them
```

---

### 1.6 A retry whose commit fails leaves no job behind
```gherkin
Given a failed generation belonging to the caller
And the retry's transaction fails after the point where the job would be enqueued
When the request returns
Then no background job exists for that generation
And no worker picks up a generation that does not exist
```

### 1.7 An enqueue that times out resolves to a defined outcome
```gherkin
Given a failed generation belonging to the caller
And the job queue blocks past the enqueue timeout
When the caller retries it
Then the request returns within its budget rather than hanging
And the outcome is a stated failure, not an internal error
And replaying the same idempotency key afterwards leaves exactly one job
```

### 1.8 A generation whose enqueue was lost is still picked up
```gherkin
Given a retry whose generation committed but whose job was never published
When recovery runs
Then the job is delivered exactly once
And the generation reaches a terminal status
```

---

## 2. Retry ↔ Stale-Generation Sweep

### 2.1 The sweep does not requeue a generation the user has already retried

```gherkin
Given a failed generation that the caller has retried
When the stale-generation sweep runs
Then the failed source is not requeued
And only the new generation is processed
```

### 2.2 A row the sweep is currently requeueing cannot be retried by the user

```gherkin
Given a non-terminal generation past the stale threshold
When the caller attempts to retry it
Then the retry is refused as not-failed
And the sweep's requeue is the only path that reruns it
```

### 2.3 A retry and a sweep requeue racing on one source produce one running generation

```gherkin
Given a source generation that the sweep and a user retry act on at the same time
When both complete
Then exactly one new run exists for that source
And no duplicate document is produced
```

---

### 2.4 A generation whose document was written but never marked terminal is not run again
```gherkin
Given a retried generation whose document was written but whose terminal status
  write did not land
When the sweep requeues it and the worker runs it again
Then exactly one document exists for that generation
And no second card appears in the feed
```

### 2.5 One row failing mid-sweep neither rolls back nor blocks the rest
```gherkin
Given a sweep batch in which one row's requeue fails
When the run completes
Then rows requeued before it stay requeued and are not re-attempted next tick
And rows after it are still requeued
And the run's outcome names the failed generation rather than only a count
```

### 2.6 Two sweep activations do disjoint work
```gherkin
Given a sweep activation still running when the next one starts
When both proceed
Then no row is requeued twice
And no generation is re-triggered twice
And a holder that disappears does not block the next activation indefinitely
```

### 2.7 An always-failing generation stops being requeued and does not stall the queue
```gherkin
Given a generation whose worker fails on every attempt
And a valid generation queued behind it
When the queue is drained
Then the valid generation still completes
And the always-failing one is set aside rather than requeued without end
```

---

## 3. Worker Outcome Reaching the Feed

### 3.1 A retried generation that completes replaces its card with a document

```gherkin
Given a retried generation processed successfully by the worker
When the caller reloads the feed
Then the new generation appears as a document
And the failed source is still listed beside it
```

### 3.2 A retried generation that fails again is retryable once more within the cap

```gherkin
Given a retried generation that the worker fails
When the caller reloads the feed
Then the new generation is listed as failed and retryable
And retrying it consumes one more of the source's retry budget
```

### 3.3 A worker outcome written while the caller is paging does not corrupt the page

```gherkin
Given the caller is reading the second page of the feed
And the worker completes a generation in the same window
Then the page is returned without error
And no item appears with a kind that contradicts its identity
```

### 3.4 A job delivered twice for one generation produces one document
```gherkin
Given the same job delivered twice for one generation
When both deliveries are processed
Then exactly one document is produced
And exactly one generation-provider call is made
And the second delivery is a no-op
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `one background job is enqueued` | One arq job on the generation queue |
| `the job queue is unavailable` | Queue client raises on enqueue |
| `refused as not-failed` | 409 `GENERATION_NOT_FAILED` |
| `the stale threshold` | `GENERATION_STALE_AFTER_MINUTES` (default 10) |
| `the stale-generation sweep` | `RequeueStaleGenerations` scheduled job |
| `the source's retry budget` | 5 retries per source generation, else 429 `RETRY_LIMIT_REACHED` |
| `the enqueue timeout` | Finite timeout on the arq enqueue call |
| `recovery` | Outbox drain or the stale-generation sweep, whichever the design adopts |
| `set aside` | Dead-lettered, or driven to terminal `failed` by a bounded attempt count (story 1 owns the cap) |
| `a holder that disappears` | Sweep lease with expiry, released without operator action |
