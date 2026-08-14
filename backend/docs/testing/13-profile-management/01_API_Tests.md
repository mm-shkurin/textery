<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — token guards → read the profile → rename
> validation → rename happy path & persistence → write-path integrity (server-owned fields,
> presence, re-run safety) → transport boundary & disclosure.

# Profile management — API Tests

Endpoints: `GET /api/v1/auth/me` (read), `PATCH /api/v1/auth/me` (write). Contract:
`endpoints.md`, `api-specs/auth_me_get.yaml`, `api-specs/auth_me_update.yaml`.

> **Persistence assertions re-read in a separate session.** `create_session_factory` sets
> `expire_on_commit=False` and `find_by_id` is `session.get`, so a same-session re-read is
> served from the identity map and passes on a row Postgres never received. Wherever a
> scenario says «a fresh read of the stored profile», that is the requirement, not a phrasing
> choice — see `13_ProfileManagement_Notes.md` § Technical Warnings.

---

## 1. Token Guards

Not the generic unauthenticated case — these are the three refusals this story's own token
handling can get wrong, plus the boundary that proves the expiry check is not inverted.

### 1.1 A refresh token is refused on both routes
```gherkin
Given a signed-in account holding a refresh token
When it presents that token to read its profile
And it presents that token to rename itself
Then both requests are refused as unauthorized
And no name is stored
```

### 1.2 A token whose type claim is absent or unknown is refused
```gherkin
Given a token whose type claim is absent
And a token whose type claim is neither access nor refresh
When each is presented to read the profile
Then both requests are refused as unauthorized
```

### 1.3 A token one second past expiry is refused, and one second before it is served
```gherkin
Given an access token whose expiry has just passed
When its holder reads the profile
Then the request is refused as unauthorized
Given an access token one second short of expiry
When its holder reads the profile
Then the profile is returned
```

### 1.4 A valid token whose account no longer exists is refused as unauthorized
```gherkin
Given a structurally valid access token for an account whose row has been removed
When its holder reads the profile
Then the request is refused as unauthorized
And the refusal is indistinguishable from the refusal of a forged token
```

---

## 2. Read the Profile

### 2.1 The profile reports the caller's own email, name and registration date
```gherkin
Given an authenticated account that has set a name
When it reads its profile
Then the returned email is the address it registered with
And the returned name is the name it set
And the returned registration date is the instant the account was created
```

### 2.2 An account that never set a name reports the name as present and null
```gherkin
Given an authenticated account that has never set a name
When it reads its profile
Then the response carries the name key
And its value is null
```

### 2.3 The profile carries no verification status
```gherkin
Given an authenticated account
When it reads its profile
Then the response carries exactly the email, the name and the registration date
And it carries no verification status and no account identifier
```

### 2.4 The registration date is a UTC instant regardless of the stored offset
```gherkin
Given an account whose registration instant is stored with a non-UTC offset
When it reads its profile
Then the registration date is reported as the equivalent UTC instant
And it is rendered in the same form as every other timestamp on this product's wire
```

### 2.5 A registration instant with no timezone is a server fault, named
```gherkin
Given an account whose registration instant carries no timezone
When it reads its profile
Then the read fails naming the registration date as the cause
And it does not silently report the instant shifted by the host's offset
```

### 2.6 The registration instant crosses the wire at full precision
```gherkin
Given an account whose registration instant carries a non-zero fraction of a second
When it reads its profile
Then the reported instant matches the stored one exactly, fraction included
```

*2.4 is satisfied by a serializer that truncates to whole seconds — "the equivalent UTC
instant" says nothing about precision.*

### 2.7 The registration instant does not follow the server's own timezone
```gherkin
Given the application running with its process timezone set away from UTC
When an authenticated account reads its profile
Then the reported registration instant is the same UTC instant as under a UTC process
```

*The container and CI are UTC by accident, not by contract; a code path reading local
system time is invisible until the first non-UTC host.*

### 2.8 Both routes forbid caching
```gherkin
Given an authenticated account
When it reads its profile
And when it renames itself
Then both responses forbid storing the body
```

---

## 3. Rename — Validation

### 3.1 A raw value over the input cap is refused before normalization, with its own code
```gherkin
Given an authenticated account
When it submits a name longer than the raw input cap
Then the rename is refused as a bad request
And the failure names the input cap, not the name bound
And a fresh read of the stored profile shows the name unchanged
```

### 3.2 The raw cap accepts its last legal value and refuses the first illegal one
```gherkin
Given an authenticated account
When it submits a name of exactly the raw input cap
Then the rename is accepted
When it submits a name one code point longer
Then the rename is refused naming the input cap
```

### 3.2a The raw cap counts code points, not units or bytes
```gherkin
Given an authenticated account
When it submits a name of the raw input cap's worth of astral characters
Then the refusal names the name bound, not the input cap
```

*A raw gate written over byte length or UTF-16 units refuses that value at the cheap gate,
and 3.1 and 3.2 both stay green — they never vary the unit.*

### 3.3 The name bound is applied after normalization, and counts code points
```gherkin
Given an authenticated account
When it submits a name of exactly the name bound
Then the rename is accepted
When it submits a name one code point longer
Then the rename is refused as an invalid name
```

### 3.4 A composed name is measured after normalization, not before
```gherkin
Given an authenticated account
When it submits a name written as base and combining pairs that normalizes to exactly the bound
Then the rename is accepted
And a fresh read of the stored profile returns a value canonically equivalent to what was sent
```

### 3.5 A name of exactly the bound in astral characters round-trips unchanged
```gherkin
Given an authenticated account
When it submits a name of the bound's worth of astral characters
Then the rename is accepted
And a fresh read of the stored profile returns that name character for character
```

### 3.4a Normalization actually runs, and the response is the normalized value
```gherkin
Given an authenticated account
When it submits a name in decomposed form
And a second account submits the same name in composed form
Then a fresh read of each stored profile returns byte-identical values
And the decomposed submission's response body carries the composed form, not the submitted bytes
```

*3.4 asserts canonical equivalence, which an implementation that stores the raw bytes and
never normalizes satisfies exactly — and then two users who typed the same name are stored
differently, and the client's dirty flag never clears after such a save.*

### 3.6 Control and surrogate code points are refused, not stripped
```gherkin
Given an authenticated account
When it submits a name consisting of a single null character
And it submits a name containing an unpaired surrogate
Then each rename is refused as an invalid name
And neither is reported as a server fault
```

### 3.6a A name carrying storage metacharacters is stored as written
```gherkin
Given an authenticated account
When it submits a name containing quote, backslash, percent and underscore characters
  alongside a fragment shaped like a query clause
Then the rename is accepted
And a fresh read of the stored profile returns it character for character
And no other account row is affected
```

*The scan dismissed injection because the ORM parameterizes — that is the mitigation, not a
guard. This is the round-trip proof for the storage sink, which the astral and decomposed
fixtures do not give.*

### 3.7 A non-string name is refused by this contract's own failure shape
```gherkin
Given an authenticated account
When it submits a number as the name
And it submits a list as the name
And it submits an object as the name
Then each rename is refused as an invalid name in this product's canonical failure form
And no failure body repeats the rejected value back to the caller
```

### 3.8 A body that is not JSON is the one shape this contract does not own
```gherkin
Given an authenticated account
When it submits a body that is not valid JSON at all
Then the request is refused
And the refusal is the framework's own validation shape, not this contract's failure form
```

*Pinned deliberately: closing this means an application-wide validation handler that
changes the failure contract of all nineteen existing endpoints (`endpoints.md`).*

---

## 4. Rename — Clearing and the Tri-State

### 4.1 A blank name clears the stored name
```gherkin
Given an authenticated account that has set a name
When it submits an empty name
Then the rename is accepted
And a fresh read of the stored profile reports no name
```

### 4.2 An omitted name leaves the stored name untouched
```gherkin
Given an authenticated account that has set a name
When it submits a rename carrying no name key at all
Then the request is accepted
And a fresh read of the stored profile still reports the original name
```

### 4.3 An explicit null name clears the stored name
```gherkin
Given an authenticated account that has set a name
When it submits a null name
Then the rename is accepted
And a fresh read of the stored profile reports no name
```

### 4.4 A name of only invisible characters clears rather than persisting
```gherkin
Given an authenticated account that has set a name
When it submits a name made only of zero-width and non-breaking space characters
And it submits a name made only of a Hangul filler
And it submits a name made only of a blank Braille pattern
Then each is accepted as a clearing
And after each, a fresh read of the stored profile reports no name
```

### 4.5 A cleared account and a never-named account are indistinguishable at rest
```gherkin
Given an account that cleared a name it had set
And a freshly registered account that never set one
When the stored profile of each is read fresh
Then both report no name
And neither stores an empty name in place of no name
```

---

## 5. Rename — Persistence Integrity

### 5.1 A rename leaves the rest of the account row untouched
```gherkin
Given a verified account with a recorded count of failed sign-in attempts
When it renames itself
Then a fresh read of the whole stored row shows the new name
And its verification status, failed-attempt count, email and registration date are unchanged
```

### 5.2 A rename writes only the name
```gherkin
Given an authenticated account
When it renames itself
Then exactly one update reaches the database
And that update sets the name and no other column
```

*The guard is the shape of the emitted statement. Two concurrent renames issued together are
**not** this guard — they serialize, and a test that goes green on the defect it names
certifies the bug (`13_ProfileManagement_Notes.md`).*

### 5.3 Renaming one account leaves every other account untouched
```gherkin
Given two accounts that have each set a name
When one of them renames itself
Then a fresh read of the other account's stored profile shows its name and email unchanged
```

### 5.4 Repeating the same rename is safe
```gherkin
Given an authenticated account
When it submits the same rename twice
Then both requests are accepted
And exactly one account row exists for it
And a fresh read of the stored profile reports that name
```

### 5.5 A rename commits once, and a refused rename commits not at all
```gherkin
Given an authenticated account
When it renames itself successfully
Then the work is committed exactly once
When it submits a name past the bound
Then no commit occurs
```

### 5.5a A failure between the write and the commit leaves the old name stored
```gherkin
Given an authenticated account with a stored name
When its rename reaches the database and the commit is then forced to fail
Then a fresh read of the stored profile reports the previous name
And no other connection ever observes the new one
```

*5.5's negative half provokes a validation refusal, which short-circuits before any write
and therefore proves nothing about rollback; the database-unavailable case never lets the
statement leave the process. This is the only scenario that exercises write-then-fail.*

### 5.5b A rename against a removed account mutates nothing
```gherkin
Given a structurally valid access token whose account row has been removed
When its holder renames itself
Then the request is refused as unauthorized
And no row exists for that account afterwards
And the total account row count is unchanged
```

*1.4 asserts only the refusal. An upsert-shaped write branch resurrects the row and the
refusal still reads as a clean 401.*

### 5.6 A freshly registered account starts with no name
```gherkin
Given a newly registered account
When its stored profile is read fresh
Then it reports no name
And it does not report an empty name
```

---

## 6. Rename — Response and Mass Assignment

### 6.1 A rename answers with the whole profile, normalized
```gherkin
Given an authenticated account
When it submits a name with surrounding whitespace
Then the response carries the email, the registration date and the trimmed name
And the caller needs no second read to learn its new identity
```

### 6.2 Server-owned fields sent alongside a name are never persisted
```gherkin
Given an authenticated account
When it submits a valid name alongside a different email
And alongside a verification status, a registration date, a password, a failed-attempt count
And alongside an account identifier
Then a fresh read of the stored row shows only the name changed
And every one of those fields holds its previous value
```

### 6.3 A rename cannot reach another account
```gherkin
Given two authenticated accounts
When one of them renames itself while naming the other's identifier in the body
Then only its own name changes
And a fresh read of the other account's stored profile is unchanged
```

---

## 7. Transport Boundary and Disclosure

### 7.1 An oversized body is refused at the boundary
```gherkin
Given an authenticated account
When it submits a rename whose body far exceeds the request body cap
Then the request is refused for size
And the body is not fully buffered and parsed before the refusal
```

### 7.2 The boundary refusal is reached through the path a browser takes
```gherkin
Given an authenticated account
When it submits an oversized rename through the application's own origin
Then the refusal is this product's canonical failure form
And it is not the proxy's own error page
```

*The proxy in front of the API carries no body cap today, so its default answers first with
HTML: a test that only reaches the backend port is green on a path no user takes
(`endpoints.md` § Corrected after the review passes).*

### 7.3 No failure leaks the account's identity or the system's internals
```gherkin
Given an account seeded with a distinctive email and a distinctive name
When it is refused as unauthorized
And when it is refused for an over-long name
And when the read fails as a server fault
Then no response body contains that email or that name
And no response body contains a stack trace, a file path or database syntax
And neither value appears in the captured application log
```

### 7.4 Every failure family answers the canonical failure form
```gherkin
Given an authenticated account
When each refusal this contract defines is provoked in turn
Then every response carries a failure code and a message and nothing else
```

### 7.5 Redaction is a stated substitution, not the absence of a string
```gherkin
Given an account seeded with a distinctive email, a distinctive name and a distinctive token
When each failure family is provoked in turn
Then the log shows the agreed redaction marker where each value would have stood
And no response body and no log record carries any of the three values
And none carries an escaped, percent-encoded or base64 form of them either
```

*7.3 passes on any encoding change — a JSON-escaped email or a row repr in a debug field
satisfies "does not contain". The token is a credential and is covered here because the
ordinary way it leaks is a warning line echoing the rejected authorization header.*

### 7.6 A server fault is attributable after redaction
```gherkin
Given an authenticated account whose profile read is made to fail as a server fault
Then the log carries exactly one record for that request
And that record carries a correlation identifier that also appears in the response
```

*Written as counter-pressure to 7.3 and 7.5, which are fully satisfied by a 500 that logs
nothing an operator could trace. Redaction and attribution must be pinned together or one
silently defeats the other.*

---

## 8. The Published Contract

### 8.1 Neither schema declares a length in a unit the domain does not use
```gherkin
Given the published contracts for both profile routes
Then neither declares a maximum length on the name
And a body carrying the bound's worth of astral characters validates against the published schema
```

*OpenAPI counts UTF-16 units and the domain counts code points; they split at exactly the
astral boundary these tests assert, so a well-meant `maxLength: 60` makes a generated client
refuse a name the server accepts (`endpoints.md`). Nothing else in this spec would go red on
that edit.*

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `an authenticated account` | Registered + verified account, valid access token in `Authorization: Bearer` |
| `it reads its profile` | `GET /api/v1/auth/me` |
| `it renames itself` / `submits a name` | `PATCH /api/v1/auth/me` with `{"name": …}` |
| `a fresh read of the stored profile` | Re-read through a **new** SQLAlchemy session (not `expire_on_commit=False` identity map) against real Postgres |
| `a fresh read of the whole stored row` | Direct row select of `email`, `name`, `is_verified`, `created_at`, `failed_attempt_count` |
| `the raw input cap` | 256 code points, checked before trim/NFC → `NAME_INPUT_TOO_LARGE` |
| `the name bound` | 60 code points after trim + NFC → `INVALID_NAME` |
| `astral characters` | U+1F600 and friends — 1 code point, 2 UTF-16 units, 4 UTF-8 bytes |
| `base and combining pairs` | NFD input, 120 raw code points normalizing to 60 |
| `this product's canonical failure form` | `{"error_code": …, "message": …}` via `exception_handlers.py` |
| `exactly one update reaches the database` | `before_cursor_execute` capture, idiom of `test_generation_storage_cas_shape.py` |
| `the work is committed exactly once` | Real `SqlAlchemyUnitOfWork` bound to the repository session; wiring shape of `test_login_wiring.py` |
| `the request body cap` | 2 MiB application cap (`api-specs/README.md`); proxy cap 4 MiB above it |
| `the application's own origin` | `app_url` (through nginx), not `BACKEND_PORT` |
| `forbid storing the body` | `Cache-Control: no-store` on every response of both routes |
