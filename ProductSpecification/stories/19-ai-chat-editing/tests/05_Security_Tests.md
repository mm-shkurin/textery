# AI chat editing — Security Tests

Attack surface: seven owner-scoped endpoints, a free-text instruction that reaches a
model and a log, model output that becomes stored document HTML, and a server-sent event
stream whose framing is built from that output. Generic 401 handling, security headers,
CORS and transport are cross-cutting and are not repeated here.

§1.1, §2.4, §3.1, §3.2 and §4.2 restate guards the API suite carries (`01_API_Tests.md`
§1.1, §2.7, `_Apply` §6.7, `_Lifecycle` §5.5, §4.1). They are implemented ONCE, in the API
suite, and referenced here so the attack surface reads complete — not written twice.

---

## 1. Authorization and object access

### 1.1 Every endpoint is owner-scoped and leaks no existence
```gherkin
Given an authenticated user
When they invoke <endpoint> for a document owned by another account
Then the request is refused as not found, never as forbidden
And the body is byte-identical to the same call for a document id that does not exist
And no state changes on the other account's document
```
Cover each of the seven endpoints separately as <endpoint>.

### 1.2 Identifiers from a sibling resource are rejected, not silently accepted
```gherkin
Given an authenticated user owning two documents
When they use the first document's edit identifier under the second document's path
And they use the first document's revision number under the second document's path
Then both are refused as not found
And no edit is streamed, cancelled or restored
```

### 1.3 A stale document reference cannot outlive its version
```gherkin
Given an edit queued against a document version
When the document is changed by another request before the edit applies
Then the edit does not overwrite the newer content
```

---

## 2. Input handling

### 2.1 Injection payloads in the instruction reach the datastore as data
```gherkin
Given an authenticated user owning a document
When they submit an instruction containing datastore control syntax
Then the instruction is stored and returned literally
And the document, its revisions and its messages are unaffected
```

### 2.2 Instruction and selection bounds are enforced in code points
```gherkin
Given an authenticated user owning a document
When they submit an instruction at and beyond the maximum length using multi-byte text
And they submit selection offsets at and beyond the document length using multi-byte text
Then each over-limit request is refused
And no edit is created
```

### 2.3 A forged log prefix in the instruction produces one log record
```gherkin
Given an authenticated user owning a document
When they submit an instruction containing newline characters and a forged log prefix
Then exactly one structured log record is produced for the submission
```

### 2.4 Server-owned fields cannot be set from the body
```gherkin
Given an authenticated user owning a document
When they submit an instruction whose body also carries server-owned fields
Then every stored value is the server-derived one
When they send a body to the restore endpoint
Then it is ignored entirely and the restored content comes only from the named revision
```

---

## 3. Output safety

### 3.1 Model output is neutralised before it is stored or displayed
```gherkin
Given an edit whose model output contains a script element, an inline event handler and
  a scripting-scheme link
When the edit completes
Then the stored document contains none of them
And re-reading the document returns the neutralised content
```
Repeat with upper-case markup under a locale whose case folding is not invariant.

### 3.2 Model output cannot forge stream events
```gherkin
Given an edit whose model output contains event-stream framing and a forged terminal event
When a client reads the stream
Then the payload arrives as one chunk event with its text intact
And the client observes exactly one terminal event, the server's own
```

### 3.3 No error path discloses internal detail
```gherkin
Given a seeded sentinel value in the datastore text, the prompt, the provider payload and
  the credentials
When each failure path is exercised
Then every response, stream event and log record carries the fixed redaction marker in
  place of the sentinel
```
Assert on the presence of the marker, not merely on the absence of the raw value.

---

## 4. Abuse resistance

### 4.1 The daily quota cannot be exceeded by racing
```gherkin
Given an account one edit below its daily quota
When several instructions are submitted concurrently
Then exactly one is accepted
And the rest are refused as over quota
And the counter never exceeds the quota and never goes negative
```

### 4.2 A single document cannot be driven into parallel edits
```gherkin
Given an authenticated user owning a document
When several instructions and a restore are submitted concurrently
Then exactly one mutation is admitted
And the others are refused as conflicts
```

---

## 5. Hazard Guards

Folded in from the hazard-catalogue scan.

### 5.1 Every authentication failure looks the same on every endpoint
```gherkin
Given a request bearing a token that is <kind>
When it is sent to <endpoint>
Then it is refused as unauthenticated
And the status and body are byte-identical across every kind and every endpoint
```
Cover each kind separately: <kind> in {absent, malformed, expired, a non-access token};
cover all seven endpoints. The stream endpoint answers with the same error body, not with
an event stream.

### 5.2 The cancel endpoint binds nothing from its body
```gherkin
Given an authenticated user owning a document with a live edit
When they cancel it with a body carrying server-owned fields
Then none of those values reaches the stored edit
```
The cancel contract declares no body, which is exactly the shape that acquires a
permissive binder by accident.

### 5.3 An instruction cannot forge the provider's own message structure
```gherkin
Given an authenticated user owning a document
When they submit an instruction containing the provider's role and delimiter framing
Then the assembled provider request carries it as data inside a single user message
And the request has exactly the intended number of role segments
```

### 5.4 Every failure family returns the sanctioned error shape
```gherkin
Given <failure family>
When it is exercised
Then the response body and, where applicable, the terminal stream event match the
  sanctioned error shape
And neither carries a stack frame, a datastore keyword, an internal type name or a
  filesystem path
And a correlation identifier is present so the detail is findable in the server log
```
Cover each separately: <failure family> in {datastore unavailable, broker unavailable,
provider server error, provider timeout, provider malformed body, version conflict,
quota-store failure, unhandled exception}.

### 5.5 A successful edit does not leak the document into the logs
```gherkin
Given a document seeded with a sentinel value
When an edit completes successfully
Then no routine log record carries the sentinel
And where the value must appear it is replaced by the fixed redaction marker
```
The existing disclosure scenario covers failure paths only; the happy path is where the
full document is routinely handed to a third party and to the log.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `<endpoint>` | Each of the seven story endpoints in `endpoints.md` |
| `datastore control syntax` | SQL metacharacters and statement terminators in the message field |
| `a forged log prefix` | Carriage return and newline followed by a fake log-level prefix |
| `the fixed redaction marker` | The constant substituted for redacted values in responses and logs |
| `a locale whose case folding is not invariant` | Turkish locale, exercising the dotless-i case pair |
