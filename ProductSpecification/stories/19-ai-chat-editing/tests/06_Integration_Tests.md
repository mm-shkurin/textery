# AI chat editing — Integration Tests

The external system is the document-edit provider — a port of its own, separate from the
generation provider. These scenarios exercise the worker against a driven fake of that
port; the real provider is never called from tests.

---

## 1. Provider success flow

### 1.1 A provider response becomes a revision, a reply and a terminal event
```gherkin
Given a queued edit
When the provider returns its result in several parts
Then each part is recorded as an event in order
And the result is applied as a new document version
And a revision and an assistant message are recorded
And a terminal done event carrying that version and revision is emitted last
```

### 1.2 A provider reply that changes nothing is still a completed edit
```gherkin
Given a queued edit whose provider response asks a clarifying question instead of
  rewriting the document
When the edit completes
Then the document content and version are unchanged
And no revision is written
And the assistant message is recorded
And the terminal event reports that nothing changed
```

---

## 2. Provider failure modes

### 2.1 Each provider failure ends the edit with its own terminal code
```gherkin
Given a queued edit
When the provider fails with <failure>
Then the edit ends in a terminal error carrying the code for <failure>
And no partial content is applied
And the quota charge is refunded where the failure is not the model's own refusal
```
Cover each failure separately: <failure> ∈ {connect timeout, read timeout, client error,
server error, malformed body, empty body, truncated mid-response}.

### 2.2 A server-side provider failure is retried, a client-side one is not
```gherkin
Given a queued edit
When the provider returns a server error and then succeeds
Then the edit completes
And the provider was called more than once
When the provider returns a client error
Then the edit ends in a terminal error
And the provider was called exactly once
```
Retries are bounded and spaced with backoff and jitter, not on a fixed tick.

### 2.3 Provider timeouts are finite and configured
```gherkin
Given a provider that never answers
When an edit is executed
Then the call is abandoned at the configured connect or read timeout
And the edit reaches a terminal state within its deadline
```

---

## 3. Worker and queue integration

### 3.1 A job dequeued before its row is visible retries rather than failing
```gherkin
Given a job dequeued before its edit row has become visible
When the worker executes it
Then the job is retried
And the edit eventually completes
And it is not marked failed on the first miss
```

### 3.2 Two reaper activations do disjoint work
```gherkin
Given a set of edits past their deadline
When two stale-edit reaper activations run at the same time
Then each edit is reclaimed by exactly one activation
And no edit is requeued twice by the pair
```

### 3.3 The existing generation flow keeps working alongside the new worker
```gherkin
Given the edit worker is running
When a document generation is requested through the existing flow
Then it completes as before
And the two flows do not interfere with each other's queues or counters
```

---

## 4. Hazard Guards

Folded in from the hazard-catalogue scan.

### 4.1 A rolled-back submission never leaves a job behind
```gherkin
Given an instruction whose submission transaction fails after the job was handed to the
  queue
When the transaction rolls back
Then no job exists for that edit
And no worker ever wakes for an edit identifier that was never committed
```
The mirror of the committed-but-never-enqueued case: the enqueue must be an after-commit
effect, not an in-transaction one.

### 4.2 A retry is sized to the remaining deadline, not to a fresh timeout
```gherkin
Given an edit whose first attempt consumed most of its deadline
When the provider fails and the attempt is retried
Then the retry is bounded by the time remaining, or it is skipped
And the edit reaches a terminal state within its deadline
And the in-flight provider call is abandoned
```
Red when the retry receives a full fresh timeout and the edit runs past its deadline while
the startup ordering check still passes.

### 4.3 A poison edit does not block healthy edits behind it
```gherkin
Given an always-failing edit at the head of the queue
And an unrelated edit for another document behind it
When the worker processes the queue
Then the unrelated edit completes normally
And the failing edit exhausts its attempts and ends terminal
```

### 4.4 A reaper that dies holding its lease does not stop reclamation
```gherkin
Given a reaper activation that stops while holding the lease
When the lease expires
Then a later activation acquires it
And the backlog is reclaimed
```

### 4.5 The prompt's conversation window is bounded
```gherkin
Given a document with a conversation far longer than the configured window
When an edit is executed
Then the provider request carries at most the configured number of messages
And it never carries the whole history
```

### 4.6 A runaway provider is abandoned at the limit, not buffered whole
```gherkin
Given a provider that emits far beyond the maximum document length
When the edit is executed
Then the worker stops consuming at the limit
And the accumulated buffer and the number of recorded events are both bounded
And the edit ends in a terminal error
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the provider` | The document-edit provider port, driven by its fake |
| `a queued edit` | An edit row created by POST /ai-edits, awaiting the worker |
| `the stale-edit reaper` | The scheduled reclaim of edits past their deadline |
| `the existing flow` | Story 1's generation request path |
| `the configured connect or read timeout` | Env-configured provider timeouts, in seconds |
