> **Implementation Order**: sequential TDD — prerequisite guards → queue validation →
> queue happy path + idempotency (both directions). Continue with
> `01_API_Tests_Lifecycle.md` (sections 4-5) then `01_API_Tests_Apply.md` (sections 6-7).

# AI chat editing — API Tests (guards, validation, queueing)

Endpoints: `POST /ai-edits`, `GET /ai-edits/{edit_id}/stream`, `GET /ai-edits/{edit_id}`,
`POST /ai-edits/{edit_id}/cancel`, `GET /messages`, `GET /revisions`,
`POST /revisions/{n}/restore`. Contracts in `ProductSpecification/api-specs/`.

Split across three files for the 200-line limit; the shared DSL table lives at the end of
this file and applies to all three.

## 1. Prerequisite Guards

§1.1 is implementable first. §1.2 needs a queued edit and §1.3-1.4 a recorded revision, so
implement those three after the writes that create their preconditions (section 3 and
`01_API_Tests_Apply.md` section 7), per the read-before-write exception in the format
rules. They are grouped here as one guard family, not because they run first.

### 1.1 Every endpoint refuses an absent document indistinguishably from a foreign one
```gherkin
Given an authenticated user
And a document owned by another account
When the caller invokes <endpoint> against it
And the caller invokes <endpoint> against a document id that does not exist
Then both are refused as not found
And the two response bodies are byte-identical
And no edit, revision or message is created
```
Cover each of the seven endpoints separately as <endpoint>.

### 1.2 An edit belonging to another document of the same owner is not found
```gherkin
Given an authenticated user owning two documents
And an edit queued on the first document
When the caller requests that edit under the second document's path
Then the request is refused as not found
```
Repeat for the stream, state and cancel endpoints — the path document id is authoritative.

### 1.3 A revision belonging to another document of the same owner is not found
```gherkin
Given an authenticated user owning two documents
And a revision recorded on the first document
When the caller restores that revision number under the second document's path
Then the request is refused as not found
And no new version is created on either document
```

### 1.4 A malformed revision number is refused as not found, never as a server error
```gherkin
Given an authenticated user owning a document with revisions
When they restore revision <value>
Then the request is refused as not found
```
Cover each edge separately: <value> ∈ {zero, negative, non-integer, above the integer bound}.

---

## 2. Queue an Edit — Validation

### 2.1 An absent selection means whole-document, an explicit null does not
```gherkin
Given an authenticated user owning a document
When they submit an instruction with the selection field <selection_form>
Then the outcome is <outcome>
```
Cover each edge separately: <selection_form> ∈ {omitted → whole-document edit; explicit
null → malformed; both fields null → malformed; both zero → invalid; start ≥ end →
invalid; end past the document length → invalid}. No form silently becomes a
whole-document rewrite.

### 2.2 A missing or zero base version is refused before any row is written
```gherkin
Given an authenticated user owning a document
When they submit an instruction with base version <value>
Then the request is refused as malformed
And no edit, chat message or quota charge is recorded
```
Cover each edge separately: <value> ∈ {omitted, null, zero, non-integer}.

### 2.3 A stale base version is refused as a conflict
```gherkin
Given an authenticated user owning a document that has been saved since it was read
When they submit an instruction against the version they read
Then the request is refused as a conflict
And no edit is created
```

### 2.4 A blank or over-long instruction is refused, measured in code points
```gherkin
Given an authenticated user owning a document
When they submit an instruction of <kind>
Then the request is refused
And no edit is created
```
Cover each edge separately: <kind> ∈ {empty; whitespace only; exactly the maximum length
in multi-byte characters → accepted; one code point over → refused}.

### 2.5 A missing idempotency key is refused before any row is written
```gherkin
Given an authenticated user owning a document
When they submit an instruction without an idempotency key
Then the request is refused as malformed
And no edit is created
```

### 2.6 A whole-document edit above the context-fit threshold requires a selection
```gherkin
Given an authenticated user owning a document larger than the context-fit threshold
When they submit an instruction without a selection
Then the request is refused with the selection-required reason
When they submit the same instruction with a valid selection
Then the request is accepted
```
Assert the threshold at one code point below, exactly at, and one above, with multi-byte
content — the threshold is measured in code points, not bytes.

### 2.7 Server-owned fields in the body are ignored, not honoured
```gherkin
Given an authenticated user owning a document
When they submit an instruction whose body also sets <field>
Then the request is accepted
And the stored edit carries the server-derived value for <field>
```
Assert per field: status, edit id, account id, document id, created at, sequence number,
quota counters, version, revision number.

---

## 3. Queue an Edit — Happy Path and Re-run Safety

### 3.1 An accepted instruction queues an edit without mutating the document
```gherkin
Given an authenticated user owning a document
When they submit a valid instruction
Then the request is accepted
And the edit is recorded as queued
And the document content and version are unchanged
And the user's message is recorded in the chat history
```

### 3.2 Replaying the same key with the same body returns the same edit
```gherkin
Given an authenticated user who submitted an instruction
When they submit the identical instruction with the same idempotency key
Then the same edit identifier is returned
And exactly one edit exists
And exactly one chat message exists
```
Assert for a sequential replay and for two concurrent submissions of the same key.

### 3.3 Reusing a key with a different body is refused, never silently ignored
```gherkin
Given an authenticated user who submitted an instruction
When they submit a different instruction with the same idempotency key
Then the request is refused as malformed
And the second instruction is not executed
And the first edit is unchanged
```

### 3.4 Re-executing the worker job for one edit produces one of every side effect
```gherkin
Given a queued edit whose job is executed twice
When both executions complete
Then the model is called exactly once
And exactly one revision is written
And exactly one assistant message is written
And the quota is charged exactly once
```

### 3.5 An edit that applied its change but died before its terminal event does not reapply
```gherkin
Given an edit whose content change committed but whose terminal event was never written
When the job is requeued and runs again
Then no second revision is written
And the model is not called again
And the edit resolves to a single terminal outcome
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `an authenticated user` | Valid access token in the Authorization header |
| `they submit an instruction` | POST /api/v1/documents/{id}/ai-edits with an Idempotency-Key |
| `they cancel the edit` | POST /api/v1/documents/{id}/ai-edits/{edit_id}/cancel |
| `they read the edit's event stream` | GET /api/v1/documents/{id}/ai-edits/{edit_id}/stream |
| `declaring the last event it received` | Last-Event-ID request header |
| `the edit state endpoint` | GET /api/v1/documents/{id}/ai-edits/{edit_id} |
| `they read its revisions` | GET /api/v1/documents/{id}/revisions |
| `they read its messages` | GET /api/v1/documents/{id}/messages |
| `they restore a revision` | POST /api/v1/documents/{id}/revisions/{n}/restore |
| `a manual save` | PUT /api/v1/documents/{id} (story 5) |
| `the model` | The document-edit provider port, driven by its fake in tests |
| `the stale-edit reaper` | The scheduled reclaim of edits past their deadline |
| `the context-fit threshold` | Env-configured code-point ceiling for whole-document edits |
