# Analytics Event Tracking — Security Tests

This story opens the product's **first write endpoint that accepts a request without a
token**. Everything else under `/api/v1` requires a Bearer token, so the scenarios below are
not routine hardening — they are the whole security surface of the change.

It also turns `GET /api/v1/auth/oauth/{provider}/start` into a write surface: five new query
parameters are bound onto the server-owned handshake row. That route is treated here as a
write endpoint, not a redirect.

Skipped as not applicable: NoSQL and LDAP injection (neither is in the stack), XXE (JSON
only), session fixation (JWT, no session cookie), CSRF (no cookie authentication — the token
travels in a header, so a cross-site form cannot carry it), and the cross-cutting concerns
tested globally (security headers, CORS, HTTPS, generic 401).

---

## 1. Forgery of the Event Stream

### 1.1 A client cannot fabricate the events the business is measured by
```gherkin
Given a visitor with no session
When it attempts to report a successful subscription
And it attempts to report a started checkout
And it attempts to report a completed generation
And it attempts to report a successful sign-in
Then every attempt is refused
And no such event is recorded
```

The endpoint is anonymous and the four subscription names are declared in the catalogue for
Stories 8 and 9. If the route accepted every declared name, anyone with a command line could
write subscription activations into the table Story 15 computes revenue from.

### 1.2 A signed-in caller cannot attach its events to another account
```gherkin
Given two accounts
When the first reports an event naming the second as its owner
Then the stored event belongs to the first
And no event belongs to the second
```

### 1.3 A caller cannot rewrite another visitor's history
```gherkin
Given a visitor identity minted in one browser
And a second browser holding its own identity
When the second reports an event carrying the first browser's identity
Then no existing event is modified
And the stored event is attributed to the caller's own account, if any
```

The visitor identity is client-asserted and forgeable by construction. This scenario pins the
blast radius — forging it can add noise, never alter or read someone else's rows.

### 1.4 A resource named in a payload confers nothing
```gherkin
Given a caller reporting an editor opening whose payload names a second account's document
When the event is reported
Then the stored event is attributed to the caller, or to no account
And the response is indistinguishable from one naming a document that does not exist
And nothing about the referenced document is read or modified
```

The editor-opening event carries a document identifier on an anonymous-capable route with a
free-form payload. The visitor identifier is declared untrusted in writing; identifiers inside
the payload are not, so Story 15 would be entitled to join them to `documents` and attribute
activity to the wrong owner.

---

## 2. Mass Assignment

### 2.1 Server-owned fields cannot be set from the event body
```gherkin
Given a visitor with no session
When it reports an event naming its own owner, moment, identifier and order position
Then every one of those values on the stored event is the server's
```

### 2.2 Server-owned fields cannot be set from the registration body
```gherkin
Given a visitor registering while naming its own address, country, device, operating system, device language, verified state, failed-attempt count and creation moment
When it registers
Then every one of those values on the stored account is the server's
And the stored device language is the one derived from the browser's language header
And the stored creation moment is the server's clock
And the account is not verified
```

### 2.3 The handshake binds only the five campaign parameters
```gherkin
Given a visitor beginning a provider sign-in whose query carries a handshake token, an expiry and a provider name alongside the five campaign parameters
When the handshake begins
Then the handshake row's own values are all server-assigned
And only the five campaign parameters came from the query
```

This story is what makes the handshake route a write surface. Every other over-binding
scenario targets the two endpoints that were already writes.

---

## 3. Injection and Output Safety

### 3.1 Hostile text in any stored field is stored, not executed, and never reflected
```gherkin
Given attribution values carrying database syntax, markup and a spreadsheet formula
When a visitor registers carrying them
Then the registration behaves normally
And a fresh read returns exactly what was sent
And no response repeats them back
```

Stored verbatim is correct here — escaping belongs at Story 15's CSV and HTML sinks, and
encoding on the way in would defeat it. What this asserts is that the values reach storage
intact and never come back out in a response.

### 3.2 Hostile text in a payload is stored, not transformed
```gherkin
Given an event whose payload values carry markup, database syntax and a spreadsheet formula
When it is reported
Then a fresh read returns each value byte-identical to what was sent
And no response body repeats them
```

Story 15 is promised verbatim storage for **both** the attribution values and the payload, and
owes the escaping at its own sinks. 3.1 makes that promise assertable for one of the two. An
implementation that escapes payload on the way in leaves every scenario green and makes Story
15 double-encode.

### 3.3 A refusal never reflects what it rejected
```gherkin
Given a visitor reporting an event whose name carries markup
And a visitor reporting an event whose identifier carries database syntax
When each is refused
Then each refusal carries the canonical error shape
And neither repeats the submitted value
And neither names a file, a class or a stack frame
```

### 3.4 A refusal caused by an internal failure discloses nothing
```gherkin
Given the event store unreachable
And separately the rate limiter's own store unavailable
And separately a caller past the rate limit
When an event is reported under each
Then each refusal carries the canonical error shape
And no body contains a stack-trace marker, a database keyword, an internal class name, a file path or any part of the connection string
And a sentinel embedded in the connection string appears in no response body
```

The three failure families with a disclosure assertion are the ones a client causes. The
database-failure path is the single most likely place a driver message carrying the connection
string, the table name or query fragments reaches an anonymous caller, and it had none.

### 3.5 Hostile text cannot forge a log entry
```gherkin
Given the event recorder fails
And an event whose payload carries line breaks and formatting directives
When it is reported
Then exactly one entry is reported for that failure
And the payload value appears as data, not as part of the message
```

### 3.6 Campaign parameters cannot forge a redirect or a header
```gherkin
Given a visitor beginning a provider sign-in whose campaign parameters carry line breaks, parameter separators, fragments and a second redirect target
When the handshake begins
Then the visitor is still redirected to the provider
And the address the visitor is sent to carries exactly the provider's expected parameters and no injected key
And the response carries no header the contract does not declare
And the callback's own redirect back to the application is likewise unaltered
```

The five values now arrive as query-string input on a route whose only output is a redirect
header — the exact sink this class names. The existing redirect scenario asserts the campaign
parameters are absent from it, using benign values.

---

## 4. Abuse Bounds

### 4.1 An anonymous flood is bounded and fails closed
```gherkin
Given a visitor reporting events past the configured rate limit
Then the excess requests are refused
And no event is recorded for them
Given the rate limiter's own store is unavailable
When a visitor reports an event
Then the request is refused
```

The second half is the one that matters: the story-wide rule «an analytics failure never
changes the user's operation» must not be read as «admit everything when the limiter breaks»,
which would leave the busiest write path in the product with no bound at all.

### 4.2 Oversized and malformed bodies are refused before they are absorbed
```gherkin
Given a request body over the transport limit declaring no length
And a payload nested far past the depth limit
And a payload carrying a null character
When each is sent to the events endpoint
Then each is refused with the canonical error shape
And none produces a server error
And none is fully buffered before refusal
```

### 4.3 Oversized and pathological headers are bounded, not parsed
```gherkin
Given a visitor registering with a browser identification far past its bound
And a visitor registering with a language list carrying thousands of tags
And a visitor registering with a browser identification built to make its parser backtrack
When each registers
Then each registration succeeds
And each request answers within the registration budget
And none produces a server error
And no account stores a truncated or partially-parsed value
And each account's device, operating system and language read as unset
```

Registration now parses two attacker-controlled **headers** into stored values, and user-agent
parsing is a known backtracking surface. «Bounded» here means the parse gives up and stores
nothing — **not** that the request is refused: a hostile `User-Agent` must not become a way to
deny someone an account, and `/auth/register` has no header-driven refusal today (Governing
Decision). Every existing scenario for these two headers uses short, well-formed values.

---

## 5. Personal Data

### 5.1 Personal data is stored in exactly one place
```gherkin
Given an account registered with a distinctive address and distinctive attribution values
When every recorded event is read
And every response the visitor received is read
And everything reported about those operations is read
And the abuse counter rows are read
Then the distinctive values appear only on the account row
```

### 5.2 The abuse counters do not store the address in recoverable form
```gherkin
Given a visitor reporting events from a sentinel address
When the counter rows are read directly
Then the sentinel address does not appear in recoverable form in any bucket key or column
```

The bucket key is the visitor's address. That was harmless while the table held only sign-in
attempts; once it keys every anonymous page view, this story's headline claim — that personal
data lives on the account row and nowhere else — is either false or depends on a derivation
nobody has stated. This scenario forces the decision.

### 5.3 Deleting an account removes its personal data and bounds what is left
```gherkin
Given an account registered from a distinctive address
When it deletes itself
Then the address is absent from the account
And its events remain, attached to no account
And the visitor's browser holds no identity or attribution linking a new account to the old one
```

### 5.4 The abuse counters do not become a permanent visitor log
```gherkin
Given many visitors reporting events across several rate-limit windows
When the windows have elapsed
Then the number of stored counter rows is bounded
```

### 5.5 Pruning elapsed counters leaves live counters and the sign-in counters alone
```gherkin
Given counter rows from a window that has elapsed
And counter rows in the current, live window
And sign-in counter rows for the same addresses
When the prune runs
Then the elapsed rows are gone
And every live-window row is unchanged
And every sign-in counter row is unchanged, elapsed ones included
And a caller already at the event rate limit is still refused
And a caller already at the sign-in limit is still refused
```

The sign-in rows are asserted unchanged **whether or not their own window has elapsed**: the
prune's predicate is scoped to this story's bucket key space, so OAuth's rows keep exactly the
lifetime and the behaviour they have today. Story 14 bounds the store it adds; it does not get
to change how the sign-in abuse bound ages out.

An unqualified delete of the whole counter table satisfies 5.4 perfectly — while destroying
every live-window count, which is the sole volume bound on the product's hottest write path and
which 4.1 requires to fail closed, and destroying OAuth's own sign-in counters, which share
that table.

### 5.6 A dependency's credential never reaches a log or a response
```gherkin
Given the geolocation dependency is configured with a distinctive credential
And that dependency fails
When a visitor registers
Then the credential appears in no reported entry
And the credential appears in no response
```

### 5.7 A presented token never reaches a log or a response
```gherkin
Given a bearer token containing a distinctive sentinel
When it is presented on the events endpoint while expired, while malformed, and while valid
Then the sentinel appears in no captured entry under any of the three
And the sentinel appears in no response body
And where the token is referenced at all it is reduced to a fixed redaction token
```

This story opens the first route that accepts a request with *or* without a token, and drives
five refused-token shapes through it — each a natural place for a handler to log the rejected
credential. The other sentinel scenarios seed data the *server* holds; this one seeds a
credential the caller supplies.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `attempts to report a successful subscription` | `POST /api/v1/analytics/events` with `SUBSCRIPTION_ACTIVATED` |
| `naming the second as its owner` | `user_id` in the request body — a field the schema does not declare |
| `whose payload names a second account's document` | A document id belonging to another account, inside `payload` |
| `a handshake token, an expiry and a provider name` | `state`, `expires_at`, `provider` supplied as query parameters to `/oauth/{provider}/start` |
| `database syntax, markup and a spreadsheet formula` | `' OR 1=1`, `<script>alert(1)</script>`, `=cmd\|'/c calc'!A1` |
| `a fresh read returns exactly what was sent` | Byte-identical after NFC, re-read in a separate session |
| `line breaks, parameter separators, fragments and a second redirect target` | `%0d%0a`, `&`, `#`, a second `redirect_uri=` inside a `utm_*` value |
| `the payload value appears as data` | A structured log field, asserted as one record — never string-interpolated into the message |
| `the rate limiter's own store is unavailable` | Fault-inject the rate-limit adapter |
| `any part of the connection string` | Sentinel seeded into the database URL, asserted absent from every response body |
| `none is fully buffered before refusal` | Bytes read at the point of refusal, not `Content-Length` |
| `built to make its parser backtrack` | A `User-Agent` fixture chosen against the chosen parser's known super-linear input, with a wall-clock ceiling |
| `everything reported` | Captured log records, asserted on a fixed redaction token |
| `the abuse counter rows` | `oauth_rate_limits` — read directly, since the eraser deliberately does not touch it |
| `in recoverable form` | The raw address, and any encoding of it reversible without a secret |
| `the number of stored counter rows is bounded` | `oauth_rate_limits` row count after elapsed-window pruning |
| `sign-in counter rows` | The OAuth-start buckets that shared this table before this story |
| `a distinctive credential` | Sentinel value in the geolocation configuration |
| `a bearer token containing a distinctive sentinel` | Sentinel embedded in the token's own text, presented in the `Authorization` header |
