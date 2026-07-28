> **Implementation Order**: hazard-scan guards, part two — continues
> `01_API_Tests_Guards.md`. The determinism rule stated there applies here too.

# AI chat editing — API Tests (hazard guards: schema, boundary, time)

DSL reference: the table at the end of `01_API_Tests.md` plus the additions at the end of
`01_API_Tests_Guards.md`.

## 4. State Machine and Schema

### 4.1 Illegal transitions between non-terminal states are rejected
```gherkin
Given an edit in state <from>
When a transition to <to> is attempted
Then it is rejected and the edit is unchanged
```
Cover the skip edge (queued to done without streaming) and the reverse edge (streaming
back to queued, as a requeue must not regress status or reset event numbering), alongside
the legal edges which must be accepted.

### 4.2 An unknown constant follows the stated policy rather than being coerced
```gherkin
Given a stored <constant> whose value the reading code does not define
When it is read
Then the read fails loudly with the generic error envelope and an attributable log record
And it is not coerced to the first defined value
And no stream is crashed mid-frame
```
Cover each separately: <constant> ∈ {event type, edit status, revision source}. The policy
is stated in `ProductSpecification/api-specs/README.md`: an unrecognised STORED value is a
clean failure, because the row was written by code with a different idea of the state
machine. The wire direction is the opposite and is covered client-side in
`02_UI_Tests_Guards.md` §8.6.

### 4.3 An unknown field on the wire is ignored rather than rejected
```gherkin
Given a request body carrying a field the reader does not define
When it is submitted
Then it is accepted
And the unknown field is not persisted
```
Distinct from the server-owned-field rule: unknown means unrecognised, not protected.

---

## 5. Request Boundary

### 5.1 A malformed page size is refused, an omitted one defaults
```gherkin
Given an authenticated user owning a document with history
When they read a list with a page size of <value>
Then the outcome is <outcome>
```
Cover each edge separately on both list endpoints: <value> ∈ {omitted → the documented
default page size; zero → refused; negative → refused; non-integer → refused; above the
cap → clamped to the cap}. A malformed value must never silently become the default.

### 5.2 An empty or forged cursor is refused, not treated as the first page
```gherkin
Given an authenticated user owning a document with history
When they read a list with a cursor that is <kind>
Then the outcome is <outcome>
And no entry from another document is returned
```
Cover each edge separately, per `api-specs/README.md`: <kind> ∈ {empty → the first page,
exactly as if omitted; structurally invalid → refused as malformed; valid-looking but not
issued by this server → refused as malformed; referring to another owner's document →
refused as not found, never confirming it exists}.

### 5.7 A blank idempotency key is refused like an absent one
```gherkin
Given an authenticated user owning a document
When they submit an instruction with an empty or whitespace-only idempotency key
Then the request is refused as malformed
And no edit is created
```

### 5.8 The event tail is served by its index, not by a scan
```gherkin
Given an edit with many recorded events
When the stream tails them
Then the query plan uses the edit-and-sequence index
```
Nothing else in the suite would go red on a sequential scan: at test data sizes it is fast.

### 5.9 A non-terminal edit reports progress, not a frozen zero
```gherkin
Given an edit that is queued and then streaming
When its state is read while it is still running
Then the status reflects the current state
And the highest recorded event number advances as chunks are committed
```
This is the documented polling fallback. An implementation returning zero until the edit
finishes passes every other scenario while the fallback shows no progress and reconnects
from the start on every tick.

### 5.3 An unlisted ordering parameter is not honoured
```gherkin
Given an authenticated user owning a document with history
When they read a list supplying an ordering parameter
Then the documented fixed order is unchanged
And the supplied value is not interpolated into the query
```

### 5.4 The idempotency key is bounded
```gherkin
Given an authenticated user owning a document
When they submit an instruction with a key at the maximum length
And they submit one with a key beyond it
Then the first is accepted and the second is refused
```

### 5.5 An oversized request body is refused before its fields are parsed
```gherkin
Given an authenticated user owning a document
When they submit a request body beyond the maximum entity size
Then it is refused
And no edit row is written
```

### 5.6 Equal sort keys page in a stable total order
```gherkin
Given a document whose first mutation wrote two revisions in the same transaction
And two chat messages recorded at the same instant
When the lists are read repeatedly and paged across that boundary
Then the order is identical on every read
And each entry appears exactly once
```
The baseline-plus-result pair is written in one transaction by contract, so equal
timestamps are guaranteed, not hypothetical.

---

## 6. Time

### 6.1 The reaper reclaims at the deadline and not before
```gherkin
Given a running edit and a clock under test control
When the reaper runs at one tick before the deadline
Then the edit is untouched
When the reaper runs at the deadline and after it
Then the edit is reclaimed
```
Every deadline, timeout and expiry in this story is evaluated against the injectable
clock — advancing that clock alone must drive terminalisation, with no real time elapsed.

### 6.2 The quota becomes available exactly at the reset instant it advertises
```gherkin
Given an account at its daily quota and a clock under test control
When it submits one tick before the advertised reset instant
Then the request is refused
When it submits at that instant
Then the request is accepted
```

---
