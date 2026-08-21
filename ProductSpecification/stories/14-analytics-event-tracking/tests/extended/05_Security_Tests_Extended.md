> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — Security Tests (Extended)

---

## 1. Token Handling on the Anonymous Route

### 1.1 Every unusable token shape is refused identically
```gherkin
Given tokens that are expired, refresh-typed, of an unknown type, structurally malformed, and signed by the wrong key
When each is presented while reporting an event
Then every request is refused as unauthorized
And the refusals are indistinguishable from one another
And no event is recorded for any of them
```

### 1.2 An empty or malformed authorization header is refused, not ignored
```gherkin
Given an authorization header that is empty
And one carrying a scheme other than the expected one
When each is presented while reporting an event
Then each request is refused as unauthorized
And neither is recorded as an anonymous event
```

The failure to guard against here is silent downgrade: treating an unusable header as
«no header» would let a caller with a revoked token keep writing, indistinguishably from a
visitor who never signed in.

---

## 2. Claims a Client Should Not Be Able to Make

### 2.1 The degraded marker cannot be used to hide from the counts
```gherkin
Given a visitor with no session
When it reports events marking itself as unable to store its identity while in fact holding one
Then the events are recorded as marked
And the marker changes nothing about attribution or rate limiting
```

The marker exists so Story 15 can exclude an inflated population, not as a privilege. This
pins that a client asserting it gains nothing beyond being excluded from a count.

### 2.2 Occurrence keys cannot be used to probe what already exists
```gherkin
Given an occurrence already recorded by another visitor
When a different visitor reports an event under that same key
Then the response is indistinguishable from reporting a fresh occurrence
```

---

## 3. Input Volume

### 3.1 Attribution values at and past their bound behave as documented
```gherkin
Given attribution values exactly at the bound
And attribution values one code point over
When a visitor registers with each
Then the first is stored
And the second is not stored, while its registration succeeds
And nothing is stored truncated
And no volume of attribution text can refuse a registration
```

The bound is still a security bound — it is what stops an unbounded string reaching the
store — but on this route it is enforced by **discarding**, not by refusing. The last line is
the assertion: an attacker who wants to deny registration cannot do it by appending to a
marketing link.

Note what is deliberately *not* added: `/auth/register` carries no request-body cap today
(only `avatar_router.py` does), and this story does not give it one — that would be precisely
the new refusal reason the Governing Decision forbids. The exposure to an enormous register
body is therefore exactly what it is today, neither better nor worse; the bound's only job
here is that an over-long value is never **stored**.

### 3.2 A body that is not JSON at all is refused without disclosing internals
```gherkin
Given a request body that is not valid JSON
And a request body sent as plain text
When each is sent to the events endpoint
Then each is refused
And neither refusal names a file, a class or a stack frame
```

`endpoints.md` records that this case answers the framework's own error shape rather than the
canonical envelope, and that closing that gap is wider than this story. The assertion here is
the part this story does own: whatever the shape, it discloses nothing.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `signed by the wrong key` | JWT signed with a key other than the configured secret |
| `indistinguishable from one another` | Identical status and body across all refusals |
| `marking itself as unable to store its identity` | `degraded: true` sent by a client that in fact persisted its identity |
| `an occurrence already recorded by another visitor` | Reuse of a known `occurrence_key` across `visitor_id` values |
