> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Integration Tests (Extended)

## 1. A job enqueued for a retry survives a queue restart

```gherkin
Given a retry whose job was enqueued
When the queue is restarted
Then the job is still processed and its generation reaches a terminal status
```

## 2. A worker that crashes mid-run leaves the row to the sweep, not to the user

```gherkin
Given a retried generation whose worker crashes mid-run
When the stale threshold elapses
Then the feed labels the row recovering
And it offers no retry action
```

## 3. Retrying a generation whose source parameters are no longer supported fails cleanly

```gherkin
Given a failed generation created with a document type that is no longer offered
When the caller retries it
Then the request fails with a stated reason
And no job is enqueued
```

## 4. The worker's completion writes the document under the same owner as the source

```gherkin
Given a retried generation belonging to one account
When the worker completes it
Then the produced document belongs to that same account
```

## 5. Two retries of different sources by one account both run

```gherkin
Given two failed generations belonging to one account
When the caller retries both with distinct idempotency keys
Then two generations are created and two jobs are enqueued
```
