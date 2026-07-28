> **Implementation Order**: sections 4-5, continuing `01_API_Tests.md`. Implement after
> queueing works; continue with `01_API_Tests_Apply.md`.

# AI chat editing — API Tests (lifecycle, cancellation, streaming)

DSL reference: see the table at the end of `01_API_Tests.md`.

## 4. Lifecycle, Cancellation and Recovery

### 4.1 A second edit on a document with a live edit is refused
```gherkin
Given an authenticated user owning a document with a non-terminal edit
When they submit another instruction
Then the request is refused as a conflict
When they restore a revision
Then the request is refused as a conflict
```

### 4.2 Cancelling a live edit terminalises it with no side effect
```gherkin
Given an authenticated user owning a document with a streaming edit
When they cancel the edit
Then the edit is reported as cancelled
And no revision is written
And no assistant message is written
And the document content and version are unchanged
And the quota charge is refunded
```

### 4.3 A provider result arriving after cancellation cannot commit
```gherkin
Given an edit that was cancelled while the model was still responding
When the model result arrives afterwards
Then no revision is written
And the document version is unchanged
And no further quota is charged
```

### 4.4 Terminal states are absorbing and illegal transitions are rejected
```gherkin
Given an edit in the terminal state <state>
When <operation> is attempted against it
Then the operation is rejected
And nothing about the edit or the document changes
```
Cover each pair separately: <state> ∈ {done, error, cancelled} × <operation> ∈ {cancel,
worker apply, chunk append, stale-edit requeue}.

### 4.5 An edit abandoned by a dead worker is reclaimed and never locks the document
```gherkin
Given an edit whose worker stopped without writing a terminal event
When the stale-edit reaper runs after the deadline
Then the edit is reclaimed
And after the maximum attempt count it is driven to a terminal error
And it is never requeued again
And a later edit on the same document is accepted
```

### 4.6 A committed edit whose enqueue was lost is still executed
```gherkin
Given an edit row that was committed but never enqueued
When the stale-edit reaper runs
Then the edit is executed
And it reaches a terminal state
```

---

## 5. Streaming

### 5.1 A stream emits ordered chunks followed by exactly one terminal event
```gherkin
Given an authenticated user owning a document with a running edit
When they read the edit's event stream to completion
Then the chunk sequence numbers strictly increase
And exactly one terminal event is delivered
And the terminal kind is one of done, error or cancelled
```

### 5.2 Reconnecting replays the tail with no gap and no duplicate
```gherkin
Given a stream that was interrupted after a known event
When the caller reconnects declaring the last event it received
Then only later events are delivered, in order
And no event is repeated
```
Assert for a still-running edit, for an edit that finished during the interruption, and
after a worker requeue — sequence numbers are never reused across attempts.

### 5.3 Reconnecting at the last known event still terminates the stream
```gherkin
Given an edit that has already reached a terminal state
When the caller reads its state and reconnects declaring the last event it reports
Then the terminal event is delivered again
And the stream closes
```
This is the documented recovery path; a silent stream here is the failure being guarded.

### 5.4 An unusable last-event value replays from the start rather than failing
```gherkin
Given an edit with recorded events
When the caller reconnects declaring a last event value of <value>
Then the stream replays from the first event
And the connection does not fail
```
Cover each edge separately: <value> ∈ {negative, non-numeric, far beyond the last event}.

### 5.5 Chunk text cannot forge stream framing
```gherkin
Given an edit whose model output contains stream framing characters and a forged
  terminal event
When the caller reads the stream
Then the text is delivered as exactly one chunk event with its content intact
And no additional terminal event appears on the wire
```
Assert on the raw wire bytes, including a bare carriage return.

### 5.6 A chunk boundary inside a multi-code-unit character does not corrupt the text
```gherkin
Given an edit whose model output is split mid-emoji and mid-combining-sequence
When the caller reads the stream to completion
Then no replacement character appears in any chunk
And the concatenated text equals the final document byte for byte
```

### 5.7 A failure arrives as a terminal error event, never as a dropped connection
```gherkin
Given an edit whose provider call fails
When the caller reads the stream
Then a terminal error event with a stable code is delivered
And the stream then closes
And the same terminal state is readable from the edit state endpoint
```

---
