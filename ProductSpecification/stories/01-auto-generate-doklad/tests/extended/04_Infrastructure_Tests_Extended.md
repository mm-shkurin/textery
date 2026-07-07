> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — Infrastructure Tests (Extended)

## 1. Redis Unavailability

### 1.1 Generation submission fails cleanly when the job queue is unreachable

```gherkin
Given the job queue's backing store is unreachable
When a client submits a generation request
Then the request fails with a clear server error
And no generation is left permanently stuck in "pending" with no job ever enqueued
```

## 2. Worker Restart

### 2.1 In-flight generations are picked up again after a worker restart

```gherkin
Given a generation was mid-processing when its worker process was restarted
When a new worker instance starts
Then the generation is eventually reconciled (reprocessed or marked failed)
And it does not remain silently abandoned
```
