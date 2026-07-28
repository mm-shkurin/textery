> **Implementation Order**: hazard-scan guards, folded in from the catalogue fan-out.
> Each scenario here exists because a hazard trigger fired with no test that would go red
> on it. Implement alongside the section it references — none of these is optional.

# AI chat editing — API Tests (hazard guards)

DSL reference: see the table at the end of `01_API_Tests.md`, plus the additions at the
end of this file.

**Determinism rule for every race scenario in this story.** "Concurrently" in
`01_API_Tests.md` §3.2, `01_API_Tests_Apply.md` §6.3, §7.4 and `05_Security_Tests.md`
§4.1, §4.2 is not "start two threads and hope". Each race is driven through a barrier held
between the version read and the conditional write, and asserts the loser took the
zero-rows-affected branch. A test that passes because the interleave rarely happens is a
failed guard.

---

## 1. Text Representation

### 1.1 Multi-byte content survives a store-and-read round trip byte for byte
```gherkin
Given an authenticated user owning a document
When multi-byte content, a multi-byte instruction and a multi-byte assistant reply are
  stored and read back
Then each is byte-identical to what was submitted, in normalised form
```

### 1.2 Normalisation happens before measurement and before offsets are applied
```gherkin
Given a document submitted in decomposed form whose normalised length is shorter
When a selection-scoped edit is applied to it
Then the selection lands on the intended characters
And the length limit is measured against the normalised content
```
Red when normalisation runs after offsets are applied, or not at all.

### 1.3 Machine-readable values are produced under an invariant locale
```gherkin
Given the process is running under a locale with a comma decimal separator and a
  non-Gregorian default calendar
When list parameters and revision numbers are parsed
And revision times and the quota reset hint are rendered
Then every wire value uses the invariant representation
```

---

## 2. Re-run Safety

### 2.1 A retried attempt does not leave the previous attempt's chunks in the tail
```gherkin
Given an edit whose provider failed after several chunk events were recorded
When the job is retried and succeeds
Then a client replaying the whole tail reads the final document exactly once
And no text from the abandoned attempt appears in the replay
```

### 2.2 Replaying a key whose edit is already terminal has a defined outcome
```gherkin
Given an edit that reached <terminal state>
When the same instruction is submitted again with the same idempotency key
Then the same edit identifier is returned with that terminal state
And no second edit and no second chat message are created
```
Cover each edge separately: <terminal state> ∈ {done, error, cancelled}. A retry that
intends a fresh attempt must send a new key — see the client guard in
`02_UI_Tests_Streaming.md`.

### 2.3 A quota charge is released when the submission transaction rolls back
```gherkin
Given an authenticated user owning a document
When the quota is charged and the edit row write then fails
Then no edit exists
And the quota counter returns to its value before the request
```

### 2.4 A refund and its terminal state commit together
```gherkin
Given an edit whose worker apply loses the version check
When the terminal write fails
Then no refund exists without its terminal state
And no terminal state exists without its refund
```

---

## 3. Concurrency and Distribution

### 3.1 An edit accepted on one instance streams and cancels from another
```gherkin
Given the application running as more than one instance
When an instruction is accepted on the first instance
And its stream is read from the second instance
And it is cancelled from the third
Then the chunks and the terminal event are delivered on the second instance
And the cancellation takes effect
```
Red for any implementation holding edit state in process memory.

### 3.2 A committed event reaches an already-connected reader within the stated window
```gherkin
Given a client already reading an edit's stream
When the worker commits an event
Then the client receives it within the documented visibility window
```

### 3.3 A restore losing to a manual save is refused, not silently applied
```gherkin
Given a restore that has read the document version
When a manual save commits before the restore writes
Then the restore is refused as a conflict
And the manual save's content remains
```

### 3.4 A manual save during a live edit has a defined outcome
```gherkin
Given a document with a non-terminal edit
When a manual save is submitted from another session against the current version
Then the outcome is the documented one
And when the edit later applies, exactly one of the two is present with its version
And neither is silently overwritten
```

---

Sections 4-6 continue in `01_API_Tests_Guards2.md`.

---

## DSL Technical Reference (additions)

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a clock under test control` | The injectable clock the application reads instead of system time |
| `driven through a barrier` | Both actors held at a latch between the version read and the conditional write |
| `the documented visibility window` | The event-tail poll interval stated in the stream contract |
| `more than one instance` | Two or more application processes against one datastore |
| `the maximum entity size` | The configured request body ceiling |
