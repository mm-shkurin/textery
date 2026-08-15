> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Integration Tests (Extended)

---

## 1. Queue and Worker

### 1.1 A job enqueued for a retry survives a queue restart
```gherkin
Given a retry whose job was enqueued
When the queue is restarted
Then the job is still processed and its generation reaches a terminal status
```

### 1.2 A worker that crashes mid-run leaves the row to the sweep, not to the user
```gherkin
Given a retried generation whose worker crashes mid-run
When the stale threshold elapses
Then the feed labels the row recovering
And it offers no retry action
```

### 1.3 The worker's completion writes the document under the same owner as the source
```gherkin
Given a retried generation belonging to one account
When the worker completes it
Then the produced document belongs to that same account
```

### 1.4 Two retries of different sources by one account both run
```gherkin
Given two failed generations belonging to one account
When the caller retries both with distinct idempotency keys
Then two generations are created and two jobs are enqueued
```

---

## 2. Provider Behaviour

### 2.1 Retrying a generation whose source parameters are no longer supported fails cleanly
```gherkin
Given a failed generation created with a document type that is no longer offered
When the caller retries it
Then the request fails with a stated reason
And no job is enqueued
```

### 2.2 A provider rate-limit answer marks the retry failed, not lost
```gherkin
Given the provider refuses with a rate-limit answer
When the caller retries a failed generation
Then the new generation ends as failed
And the feed offers to retry it again
```

### 2.3 A provider answer in an unexpected shape fails closed
```gherkin
Given the provider answers with content the flow cannot parse
When the caller retries a failed generation
Then the generation ends as failed
And nothing unparsed is stored
```

---

## 3. Cross-Flow

### 3.1 A retry that completes can be converted like any generation
```gherkin
Given a retry that completed
When it is converted into a document
Then the document appears in the feed in place of the generation
```

### 3.2 Deprecated list endpoints keep answering while the feed is used
```gherkin
Given the projects feed is in use
When the older document and generation list endpoints are called
Then both still answer as their contracts describe
```

---

## DSL Technical Reference

Inherits `06_Integration_Tests.md`.
