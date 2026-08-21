<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/01_API_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — ingest guards → ingest happy path → re-run
> safety on the ingest key → registration context → the server-side emitters, each bound to
> its transition → ordering → deletion → isolation of the analytics path from the product.

# Analytics Event Tracking — API Tests

Endpoints: `POST /api/v1/analytics/events` (new), `POST /api/v1/auth/register` and
`GET /api/v1/auth/oauth/{provider}/start` (both extended). Contracts: `endpoints.md`,
`api-specs/analytics_events_create.yaml`, `api-specs/auth_register.yaml`,
`api-specs/oauth_start.yaml`.

> **Persistence assertions re-read in a separate session.** `create_session_factory` sets
> `expire_on_commit=False`, so a same-session re-read is served from the identity map and
> passes on a row Postgres never received. Wherever a scenario says «a fresh read», that is
> the requirement, not a phrasing choice.

> **A refusal is only ever an option on the new endpoint.** `POST /api/v1/analytics/events` is
> this story's own route and may refuse whatever it must. `POST /auth/register` and
> `GET /auth/oauth/{provider}/start` are existing routes that Story 14 only rides along on:
> no scenario in this file may require them to answer a status code or an `error_code` they do
> not answer today. Where analytics input is unusable there, the assertion is on what was
> **stored**, never on what was **answered** — the Governing Decision in
> `14_AnalyticsEventTracking.md`, agreed 2026-08-19.

> **«An event is recorded» never means «the call answered 200».** Every emitter in this story
> hangs off a path that returns success without writing. Scenarios below assert the stored
> row, never the response code, unless the response is what is under test.

> **Single-process green is not green.** The backend runs as multiple instances
> (`.claude/rules/coding-rules.md`). Every dedupe, rate-limit and handshake scenario below
> that says «another instance» means exactly that: a second session/process sharing only the
> database. A per-process dictionary satisfies the single-instance phrasing and fails in
> production.

---

## 1. Ingest Guards — Identity

### 1.1 An event with no token is recorded as anonymous
```gherkin
Given a visitor with no session
When it reports a site visit
Then the event is recorded
And the stored event has no account attached
```

### 1.2 An event from a signed-in caller is attributed to that account
```gherkin
Given a signed-in account
When it reports opening the editor
Then the stored event is attributed to that account
And the stored event carries the visitor identifier the caller sent
```

### 1.3 A present but unusable token is refused, never downgraded to anonymous
```gherkin
Given a visitor presenting an expired access token
And a visitor presenting a refresh token
And a visitor presenting a structurally invalid token
When each reports a site visit
Then every request is refused as unauthorized
And no event is recorded for any of them
```

---

## 2. Ingest Guards — What May Be Reported

### 2.1 Only browser-origin event names are accepted
```gherkin
Given a visitor with no session
When it reports each of the three browser-origin events
Then each event is recorded
```

### 2.2 Server-only and subscription event names are refused from a client
```gherkin
Given a visitor with no session
When it attempts to report a successful subscription
And it attempts to report a completed generation
And it attempts to report a successful sign-in
Then every attempt is refused as an unknown event name
And no event is recorded for any of them
```

### 2.3 A malformed visitor identifier is refused and never stored raw
```gherkin
Given a visitor whose identifier is not a well-formed identifier
When it reports a site visit
Then the request is refused as an invalid visitor identifier
And no event is recorded
And no event is recorded with an empty visitor identifier
```

### 2.4 The same visitor written in any accepted form is one visitor
```gherkin
Given a visitor identifier written in upper case
And the same identifier written in lower case
And the same identifier written in its braced form
And the same identifier written in its urn form
When a site visit is reported under each
Then all four events resolve to one stored visitor
And the visitor column's declared type is the native identifier type
```

---

## 3. Ingest Guards — Payload Boundaries

### 3.1 A payload at the size limit is accepted and one byte over is refused
```gherkin
Given a visitor with no session
When it reports a site visit carrying a payload exactly at the size limit
Then the event is recorded
When it reports a site visit carrying a payload one byte over the limit
Then the request is refused as an invalid payload
And no event is recorded
```

### 3.2 A payload that is small but deeply nested or wide is refused, not crashed
```gherkin
Given a payload nested past the depth limit but under the size limit
And a payload carrying more keys than the limit but under the size limit
When a site visit is reported with each
Then each request is refused as an invalid payload
And neither request produces a server error
And each refusal returns within the normal response budget
```

### 3.3 A payload containing characters the store cannot hold is refused cleanly
```gherkin
Given a payload containing a null character
And a payload containing an unpaired surrogate
When a site visit is reported with each
Then each request is refused as an invalid payload
And neither request produces a server error
And no event is recorded for either
```

### 3.4 An oversized body is refused on bytes read, not on the declared length
```gherkin
Given a request body over the transport limit that declares no length
When it is sent to the events endpoint
Then the request is refused as too large
And the refusal carries the canonical error shape
And the whole body is never buffered
```

### 3.5 The payload limit is measured in bytes, not in characters
```gherkin
Given a payload built from characters outside the basic plane, exactly at the byte limit and far under it in character count
When a site visit is reported with it
Then the event is recorded
Given the same payload one byte over the limit and still far under the character count
When a site visit is reported with it
Then the request is refused as an invalid payload
And no event is recorded
```

### 3.6 A payload survives store and read with its values unchanged
```gherkin
Given a payload carrying a whole number above the wire format's exact-integer limit
And a decimal written with trailing zeros
And a key and a value in characters outside the basic plane
When a site visit is reported with it
Then a fresh read returns each value exactly as sent, scale included
And no number has been rewritten to a different representation
```

---

## 4. Ingest — Server-Owned Fields

### 4.1 A client cannot choose the account an event belongs to
```gherkin
Given a signed-in account
And a second account
When the first reports a site visit naming the second account
Then the stored event is attributed to the first account
And no event is attributed to the second account
```

### 4.2 A client cannot choose when an event happened
```gherkin
Given a visitor with no session
When it reports a site visit claiming a time far in the past
Then the stored event carries the server's time, not the claimed one
```

### 4.3 A client cannot choose an event's identity or its position in the order
```gherkin
Given a visitor with no session
When it reports a site visit naming its own event identifier and order position
Then the stored event carries server-assigned values for both
```

### 4.4 A field this version does not know is ignored, not refused
```gherkin
Given a visitor with no session
When it reports a site visit carrying an additional field this version does not define
Then the event is recorded
And the stored event is identical to one reported without that field
```

The frontend and backend are published as independently deployable repositories, so a newer
client reaching an older backend is routine rather than an edge. Every other scenario in this
section feeds *server-owned* fields and asserts they have no effect — a request model that
refuses unknown keys satisfies all of them and breaks every deploy where the client ships
first.

---

## 5. Ingest — Re-run Safety (inbound duplicate)

### 5.1 One occurrence reported twice is recorded once
```gherkin
Given a visitor with no session
When it reports a site visit
And it reports the same occurrence again
Then both requests succeed
And exactly one event is recorded
```

### 5.2 Two distinct occurrences from one visitor are both recorded
```gherkin
Given a visitor with no session
When it reports a site visit
And it reports a second, distinct site visit
Then two events are recorded for that visitor
```

### 5.3 A missing or malformed occurrence key is refused
```gherkin
Given a visitor with no session
When it reports a site visit with no occurrence key
And it reports a site visit with a malformed occurrence key
Then both requests are refused
And no event is recorded for either
```

### 5.4 One occurrence reported to two instances is recorded once
```gherkin
Given a visitor with no session
When it reports a site visit
And it reports the same occurrence against another instance
Then both requests succeed
And a fresh read returns exactly one event for that visitor and occurrence
And the collapse still holds after the first instance is restarted
```

A per-process set of seen keys passes 5.1 forever. This is the scenario that forces the
«done» marker into shared storage, which the multi-instance rule requires.

### 5.5 One occurrence reported twice at the same instant is recorded once
```gherkin
Given a visitor with no session
When it reports the same occurrence twice at once, interleaved at the point where the recorder decides whether that occurrence already exists
Then both requests succeed
And exactly one event is recorded
And the collapse is enforced by the store itself, not by a prior read
```

The production shape is a StrictMode double-invoke where the second request is genuinely
sent — both are in flight together. A read-then-insert dedupe passes 5.1 and 5.4 and writes
two rows here.

### 5.6 One occurrence key in two letter cases is one occurrence
```gherkin
Given a visitor reporting a site visit under an occurrence key in upper case
When it reports the same occurrence under the same key in lower case
Then both requests succeed
And exactly one event is recorded
And the occurrence key column's declared type is the native identifier type
```

The two spec documents disagree on what this key is — the story's validation table says
«bounded» with no unit or type, `endpoints.md` says a client-minted UUID that «sidesteps a
length bound and a normalization question entirely». Stored as text, case variants stop
collapsing, and collapsing is the entire reason the key exists.

---

## 6. Ingest — Abuse Bounds

### 6.1 A caller at the rate limit is served and one request over is refused
```gherkin
Given a visitor at the configured event rate limit within one window
When it reports one more event in that window
Then the request is refused as rate limited
And no event is recorded for the refused request
When the next window begins
Then its next event is recorded
```

### 6.2 Analytics traffic cannot exhaust an account's sign-in budget
```gherkin
Given a visitor that has reached the event rate limit from one address
When an account signs in from that same address
Then the sign-in succeeds
```

### 6.3 A rate limiter that cannot answer refuses the event
```gherkin
Given the rate limiter's own store is unavailable
When a visitor reports a site visit
Then the request is refused
And no event is recorded
```

### 6.4 The rate limit is one budget across every instance
```gherkin
Given two instances serving the events endpoint against one database
And a visitor that has reached the configured limit through the first instance
When it reports one more event through the second instance
Then the request is refused as rate limited
And no event is recorded
Given elapsed-window rows are pruned while a live window is being counted
Then the live window's count is not reset
```

A per-instance in-memory bucket passes 6.1, 6.2 and 6.3 and yields the limit multiplied by
the instance count on the product's hottest write path.

### 6.5 The window admits exactly at the rollover instant
```gherkin
Given a caller at the limit within one window
And the clock fixed one tick before the window ends
When it reports an event
Then the request is refused
When the clock advances to exactly the rollover instant
Then the next event is recorded
And the counter starts from one rather than resuming the exhausted bucket
```

6.1's «when the next window begins» is satisfiable by a real-time wait, which is the flaky
shape, and cannot distinguish a window that rolls at the boundary from one that rolls a
whole window late.

### 6.6 A rate limiter that does not answer does not hold the request open
```gherkin
Given the rate limiter's own store does not answer
When a visitor reports a site visit
Then the request is refused within the endpoint's normal budget
And no event is recorded
And the database connection is returned to the pool
```

### 6.7 Events refused by the limiter are counted, not merely dropped
```gherkin
Given a caller past the configured rate limit
When further events are reported
Then each refusal emits a distinguishable rate-limited signal carrying the bucket key and the event name
And events accepted within the limit emit no such signal
```

By design the client drops the refusal silently, so without this an arbitrary share of the
product's most-emitted event vanishes with nothing server-side distinguishing the limiter
from a quiet day.

---

## 7. Registration Context

### 7.1 Registration stores the caller's technical context and first-touch attribution
```gherkin
Given a visitor whose browser reports a device, an operating system and a language
And a frozen first-touch attribution set
When it registers
Then a fresh read of the account carries the address, country, device, operating system and language
And a fresh read of the account carries all five attribution values
```

### 7.2 The context survives the next write to the same account
```gherkin
Given an account registered with a full technical and attribution context
When it confirms its code
And it renames itself
And a sign-in against it fails
Then a fresh read after each step still carries every context value unchanged
```

### 7.3 An account created before this feature still reads
```gherkin
Given an account row stored without any technical or attribution context
When it is read through the repository
And its owner reads its own profile
Then both succeed
And every absent context value reads as unset, not as a placeholder
```

### 7.4 The country of an address that cannot be located is unset
```gherkin
Given a visitor registering from a loopback address
And a visitor registering from a private-network address
When each registers
Then each account's country is unset
And each registration succeeds normally
```

### 7.5 Attribution values are normalized before the bound, and dropped over it
```gherkin
Given an attribution value composed so that it exceeds the bound before normalization and fits after
When a visitor registers carrying it
Then the account stores the normalized value
Given an attribution value over the bound after normalization
When a visitor registers carrying it alongside four valid values
Then the registration succeeds exactly as it does for a visitor carrying no attribution at all
And all five attribution values on the account read as unset
And no value is stored truncated
And the discard is reported once
```

The bound decides what is **stored**, never what is **answered** — the Governing Decision in
`14_AnalyticsEventTracking.md`. The four valid values go with the bad one because attribution
is stored as a set (`B2`): a stored set is always a faithful copy of one real link.

### 7.5a Attribution never changes the registration's answer
```gherkin
Given two visitors registering with identical credentials except for their attribution
And the first carries no attribution
And the second carries an attribution value over the bound, one that is undecodable, and one carrying markup
When each registers
Then both answers carry the same status and the same shape
And neither answer names an attribution field
And both accounts exist and are usable
```

The scenario that goes red on the defect this story is most likely to ship. Every other
attribution scenario asserts what was *stored*; this one asserts that the caller cannot tell
from the response that attribution was involved at all. A `400 INVALID_UTM` would satisfy
«nothing is stored truncated» perfectly.

### 7.6 The same attribution written two ways is stored one way
```gherkin
Given a campaign name written in composed form
And the same campaign name written in decomposed form
When two visitors register, one carrying each
Then both accounts store the identical value
```

### 7.7 A client cannot supply its own address, country, device or verification state
```gherkin
Given a visitor registering while naming its own address, country, device, operating system, language, verified state, failed-attempt count and creation moment
When it registers
Then every one of those values on the stored account is the server's, not the submitted one
And the stored language is the one derived from the browser's language header
```

### 7.8 Text the store cannot hold is dropped at registration, never stored mangled
```gherkin
Given an attribution value containing a null character
And an attribution value containing an unpaired surrogate
When a visitor registers with each, and begins a provider sign-in with each
Then every registration succeeds and every sign-in proceeds to the provider
And none produces a server error
And no account is created carrying a mangled value
And every attribution value on those accounts reads as unset
And each discard is reported once
```

The events endpoint has this guard at 3.3 and refuses there, because a refusal on the new
endpoint costs one analytics row. Here the same input reaches an existing auth route, where a
refusal would cost a user their account — so the value is dropped instead. The hostile-text
scenario at `05_Security_Tests.md` §3.1 sends only well-formed text, which trips neither
failure; this one is the unstorable-text half, and it must go red both on a `500` and on a
`400`.

### 7.9 An explicitly empty attribution value and an omitted one are the same stored state
```gherkin
Given a visitor registering with four attribution values present and the fifth sent as an explicit empty value
When it registers
Then the fifth reads as unset
And the other four hold their submitted values unchanged
When another visitor registers with the fifth key omitted entirely
Then the result is identical
```

### 7.10 The highest-priority language tag wins, at every edge of the priority list
```gherkin
Given a browser offering a tag with no stated priority alongside one with a lower explicit priority
When it registers
Then the account stores the tag with no stated priority
Given a browser offering only a tag explicitly marked unacceptable
When it registers
Then the account's language reads as unset
Given a browser offering a malformed priority
When it registers
Then the registration succeeds and the language reads as unset, with no server error
```

An absent priority means the highest, so an implementation defaulting it to the lowest picks
the wrong tag; a tag marked unacceptable must never be selected, yet a naive maximum over a
single-tag header picks it.

### 7.11 An unusable language header stores nothing, never a default
```gherkin
Given a browser offering a header that is not a well-formed language tag
And a browser offering a header carrying markup and line breaks
And a browser offering no language header at all
When each registers
Then each account's language reads as unset
And none stores the raw header
And none reads as the most common language
```

The browser identification has exactly this guard; the language tag had none, so a parser
falling through to a default is green against every other scenario.

### 7.12 The attribution bound is measured in characters, not bytes
```gherkin
Given an attribution value of exactly the bound in characters outside the basic plane, four times the bound in bytes
When a visitor registers carrying it
Then the value is stored, unchanged after normalization
Given the same value one character over the bound
When a visitor registers carrying it
Then the registration succeeds
And the attribution set reads as unset
And nothing is stored truncated
```

The payload is bounded in **bytes** and the attribution values in **characters**. With an
ASCII fixture the two are the same number, so an implementation counting the wrong unit passes
both bounds. §3.5 is this scenario's mirror on the other unit.

### 7.13 The language tag is canonicalized under an invariant locale
```gherkin
Given the process running under a Turkish locale
And a browser offering a language tag containing a dotted capital I
When it registers
Then the account stores the invariant-locale canonical tag
And it is identical to the tag stored for the same browser under the default locale
```

---

## 8. Emission Bound to the Transition — Auth

### 8.1 Confirming a code records the registration once
```gherkin
Given an account that has registered but not confirmed
When it confirms its code
Then a completed registration is recorded once
```

### 8.2 Confirming the same code twice records one registration
```gherkin
Given an account that has already confirmed its code
When it confirms the same code again
Then the request still succeeds
And exactly one completed registration is recorded for that account
```

### 8.3 Two simultaneous confirmations record one registration
```gherkin
Given an account that has registered but not confirmed
When two confirmations of the same code are made at once, interleaved between the read and the conditional update
Then exactly one completed registration is recorded
And the losing confirmation's update affected no rows and emitted nothing
```

### 8.4 A first sign-in through a provider records both a registration and a sign-in
```gherkin
Given a visitor arriving through a provider for the first time
When the provider callback completes
Then a completed registration is recorded
And a successful sign-in is recorded
And both carry the identical moment
```

### 8.5 A later sign-in through the same provider records only a sign-in
```gherkin
Given an account that already exists through a provider
When it signs in again through that provider
Then a successful sign-in is recorded
And no further completed registration is recorded
```

### 8.6 Attribution frozen in the browser reaches a provider-created account
```gherkin
Given a visitor holding a frozen first-touch attribution set
When it begins a provider sign-in carrying that set
And the provider callback creates its account
Then a fresh read of the account carries all five attribution values
```

### 8.7 A pair whose second emission fails keeps the first and re-attempts nothing
```gherkin
Given a visitor arriving through a provider for the first time
And the recorder fails only on the successful sign-in
When the callback completes
Then the callback succeeds and the account exists
And a completed registration is recorded exactly once
And no successful sign-in is recorded
And exactly one failure is reported, naming which event and which visitor failed
When the same account later signs in through that provider
Then exactly one successful sign-in is recorded
And no second completed registration is recorded
```

The pair is not atomic. Without this, a half-recorded account is indistinguishable in the
data from a returning sign-in, and the outbound half — that the stored event is not
re-attempted on the next sign-in — has no other scenario.

---

## 9. Emission Bound to the Transition — Generation & Documents

### 9.1 Requesting a generation records a start and remembers the visitor
```gherkin
Given a signed-in account
When it requests a generation
Then a started generation is recorded
And the generation remembers the requesting visitor
```

### 9.2 A completed generation is recorded with the requesting visitor, from any instance
```gherkin
Given a generation requested by a signed-in account
When it completes on an instance other than the one that received the request
Then a completed generation is recorded
And the recorded event carries the original requesting visitor
```

### 9.3 A generation completed twice records one completion
```gherkin
Given a generation being completed by two workers at once
When both attempt to store their result
Then exactly one completion is recorded
And the recorded completion belongs to the result that was stored
```

### 9.4 Recovering a stalled generation records no new start
```gherkin
Given stalled generations recovered by the periodic sweep
And several instances running that sweep on the same tick
When the sweep completes
Then the number of recorded starts equals the number of generations, regardless of instance count
```

### 9.5 A retried generation records a new start only when a generation was created
```gherkin
Given a failed generation
When its owner retries it twice under one retry key
Then exactly one further start is recorded
When its owner retries it under a fresh retry key
Then exactly one more start is recorded
```

### 9.6 Saving a document records a save
```gherkin
Given a signed-in account holding a document
When it saves changed content
Then a saved document is recorded once
```

### 9.7 A save that persisted nothing records nothing
```gherkin
Given a save that has already landed
When the same save is replayed and answered as already applied
Then no further saved document is recorded
```

### 9.8 A generation that already failed records no completion
```gherkin
Given a generation already in a failed state
When a late worker attempts to complete it
Then no completion is recorded
```

### 9.9 A generation that already completed records nothing further
```gherkin
Given a generation that has already completed
When its owner retries it
Then the retry is refused
And no further started generation is recorded
When a late worker attempts to complete it again
Then no further completed generation is recorded
And the stored result is unchanged
```

Both other terminal-state scenarios enter from *failed*. The domain's state setters are bare
assignments with no legality check, so a refused retry that still emits inflates the funnel
while 9.5 and 9.8 stay green.

### 9.10 The requesting visitor survives a requeue
```gherkin
Given a generation requested by a signed-in account, carrying that request's visitor
And the generation has stalled and been requeued by the periodic sweep
When the requeued generation completes
Then a completed generation is recorded
And the recorded event carries the original requesting visitor, not an empty one
```

The requeue is a read-modify-write on the same row; a blind full-row write drops the column,
and the completion then emits with nothing. 9.2 covers another instance with no requeue in
between, and 9.4 counts starts only — neither composes the two.

### 9.11 One generation failing mid-sweep neither discards the earlier recoveries nor blocks the later ones
```gherkin
Given several stalled generations
And the recovery of one of them fails
When the sweep completes
Then every generation before the failing one stays recovered
And none of them is recovered again, nor records a further start, on the next tick
And every generation after the failing one is still recovered
And only the failing one remains for the next sweep
```

---

## 10. Ordering

### 10.1 Events for one visitor are ordered by their position, not their time
```gherkin
Given two events for one visitor written from two instances whose clocks disagree
When the visitor's events are read in order
Then the earlier cause is returned before the later effect
```

### 10.2 Two events sharing a moment have a stable, repeatable order
```gherkin
Given the two events recorded by a first provider sign-in
When the visitor's events are read repeatedly
Then the two are returned in the same order every time
```

### 10.3 A recorded moment keeps its precision and its zone
```gherkin
Given the clock fixed at a moment carrying sub-second precision
When an event is recorded
Then a fresh read returns that exact moment
And the returned moment carries its time zone
```

### 10.4 A moment recorded under a non-UTC server timezone is the same instant
```gherkin
Given the application process and the database session both running in a non-UTC zone
And the clock fixed at a known instant
When an event is recorded
Then a fresh read returns that same absolute instant, not the same wall-clock reading
And the value is identical to the one stored for the same instant under UTC
```

10.3 goes red on a *missing* zone. It cannot go red on the trap the story actually names — a
naive value carrying UTC digits round-trips correctly wherever the process runs in UTC, which
is every CI run, and is off by the offset everywhere else.

---

## 11. Account Deletion

### 11.1 Deleting an account detaches its events and keeps them
```gherkin
Given an account holding recorded events
When it deletes itself
Then its events remain
And none of them is attached to an account
And the account's technical and attribution values are gone
```

### 11.2 Deleting one account leaves every other account's events untouched
```gherkin
Given two accounts holding recorded events
And events belonging to no account
When the first account deletes itself
Then the second account's events are unchanged
And the unattached events are unchanged
And the total number of recorded events is unchanged
```

### 11.3 Deleting an account with no events changes nothing
```gherkin
Given an account holding no recorded events
When it deletes itself
Then no recorded event is modified
```

### 11.4 Removing an account row outside the eraser does not fail on its events
```gherkin
Given an account holding recorded events
When its row is removed directly, without the eraser
Then the removal succeeds
And its events remain, attached to no account
```

### 11.5 A deletion that fails part-way leaves the events attached
```gherkin
Given an account holding recorded events
And the removal of the account row will fail
When it attempts to delete itself
Then the deletion is refused
And its events are still attached to it
```

### 11.6 An event arriving during a deletion cannot break it
```gherkin
Given a deletion whose detaching of the account's events has run but whose account row has not yet been removed
When an event for that account is recorded and committed from a second session
Then the deletion still completes
And no event refers to an account that no longer exists
```

The only interesting instant in the deletion is between the detach and the removal. An insert
placed anywhere else passes trivially.

### 11.7 Detaching an account's events costs the same at any volume
```gherkin
Given an account holding many thousands of recorded events
When it deletes itself
Then the store is issued one set-based update, regardless of how many events exist
And the deletion completes within its stated wall-clock bound
And every one of that account's events is detached
```

Asserted on the statement count across two seeded volumes — a wall-clock bound alone lets a
per-row loop pass on a fast machine, inside the product's only irreversible operation.

### 11.8 An erasure with no account to scope to changes nothing
```gherkin
Given accounts holding recorded events and events belonging to no account
When the erasure is invoked with no account identified
Then no recorded event is modified
And the operation does not silently succeed as if it had erased something
```

11.3 covers a valid account with an empty *result*. This covers an absent *filter* — the one
place a missing predicate detaches every event in the table.

### 11.9 Removing an account through the object model detaches its events, never deletes them
```gherkin
Given an account holding recorded events
When the account is removed through the object model, without the eraser's detaching step
Then its events remain
And each is attached to no account
And the number of recorded events is unchanged
```

11.4 goes through raw SQL and 11.1 through the eraser, which detaches first and so leaves the
relationship empty. A cascade configured to delete children therefore passes both while
destroying events on any object-model delete path — the scar this codebase already carries in
its account eraser.

### 11.10 An event reported with a deleted account's token is refused, not silently attributed
```gherkin
Given an account that has deleted itself
And an access token it was issued before the deletion
When it reports a site visit carrying that token
Then the request is refused as unauthorized
And no event is recorded
And no event refers to an account that no longer exists
```

Tokens outlive the row. Without this the write is either a swallowed constraint violation —
the event lost with no signal — or an anonymous row, and nothing distinguishes them.

---

## 12. The Analytics Path Is Isolated From the Product

### 12.1 A failing recorder changes no product outcome
```gherkin
Given the event recorder rejects every write
When an account registers
And it confirms its code
And it signs in
And it requests a generation
And it saves a document
Then every one of those operations succeeds exactly as it does today
```

### 12.2 A failing recorder is not silent
```gherkin
Given the event recorder rejects every write
When an account confirms its code
Then a failure is reported naming the event and the visitor
Given the event recorder accepts writes
When an account confirms its code
Then no such failure is reported
```

### 12.3 A hanging recorder does not hold the caller
```gherkin
Given the event recorder does not answer
When an account registers
And it saves a document
Then each operation answers within its normal budget plus the recorder's abandonment allowance
```

### 12.4 A product operation that rolls back records no event
```gherkin
Given a save whose own commit will fail after its event would be emitted
When the save is attempted
Then no saved document is recorded
And no partially written document remains
```

### 12.5 A recorded event is readable by another connection once its call has answered
```gherkin
Given an account confirming its code
When the confirmation answers
Then a fresh read from another connection already returns the completed registration
```

### 12.6 A confirmation that rolls back records no registration
```gherkin
Given an account that has registered but not confirmed
And the confirmation's own commit will fail after its event would be emitted
When it confirms its code
Then the request fails
And a fresh read shows the account still unverified with its context values unchanged
And no completed registration is recorded
```

12.4 catches the same-session commit trap on the save path. Confirmation is the other emitter
on a business write, and the one the story names as immediately re-saving the account.

### 12.7 A recorder that answers just inside its allowance still records
```gherkin
Given the event recorder answering at the named abandonment allowance minus a margin
When an account confirms its code
Then the completed registration is recorded
And no swallowed-failure signal is reported
And the operation answers within its normal budget
```

Only the past-deadline side is otherwise tested. An allowance sized too tight, or an abandon
firing before the write commits, silently drops events that were about to land.

### 12.8 Every slow hop on one request still fits inside the caller's deadline
```gherkin
Given the geolocation dependency does not answer
And the event recorder does not answer
And the connection pool is contended to its stated ceiling
When a visitor registers
Then the registration answers within its normal budget plus the named allowances, and inside the client's stated deadline
Given the caller's deadline set below the combined worst case of those hops
When it registers and abandons the request
Then no account row and no recorded event is committed after the caller stopped waiting
And no lookup or emission is left running past that point
```

Every other scenario hangs exactly one hop. One registration traverses all three.

### 12.9 A reported event is readable by another connection once its call has answered
```gherkin
Given a visitor with no session
When its site visit report answers
Then a fresh read from another connection already returns that event
```

`endpoints.md` chose 204 over 202 precisely on this claim, and recorded that 202 «would make
the read-after-write guard unassertable». That guard is this scenario; without it nothing
goes red if the ingest write becomes a background task.

### 12.10 The two extended auth routes answer exactly as they did before this story
```gherkin
Given the set of requests the registration route accepts and refuses today
And the set of requests the provider handshake route accepts and refuses today
When each is replayed against the story's implementation, once with no attribution and once with attribution that cannot be stored
Then every accepted request is still accepted, with the same status and the same body shape
And every refused request is still refused, with the same status and the same error code
And neither route answers any status code it did not answer before
```

The one scenario that owns the Governing Decision as a whole rather than one clause of it. The
attribution scenarios each assert their own outcome; nothing else asserts that the *set* of
outcomes did not grow. `07-authorization/tests/01_API_Tests.md` §1–2 and story 16's handshake
scenarios are the reference for what «today» means, and they must pass unmodified.

### 12.11 A missing geolocation configuration is not a failed boot
```gherkin
Given the geolocation configuration absent
When the application starts
Then it starts
And one startup record names country resolution as disabled
When a visitor registers
Then the registration succeeds and the account's country reads as unset
And no failure to resolve is reported, because none was attempted
```

An analytics dependency that can refuse to boot the product is the deployment-level form of
the defect 7.5a guards at the request level. The disabled signal is what keeps «unset» loud —
it must be distinguishable from both a resolution failure (Infra 2.2) and a legitimate NULL.

---

## 13. Disclosure

### 13.1 Personal data lives on the account and nowhere else
```gherkin
Given an account registered with a distinctive address and a distinctive attribution value
When every recorded event for that account is read
And every response the visitor received is read
And everything the system reported about those operations is read
And the abuse counter rows are read
Then the distinctive values appear only on the account itself
```

### 13.2 A refusal never echoes what was rejected
```gherkin
Given a visitor reporting an event whose name carries markup
And a visitor reporting an event whose visitor identifier carries a query fragment
When each is refused
Then each refusal carries the canonical error shape
And neither refusal repeats what was submitted
And neither refusal names an internal detail
```

### 13.3 A stored event name this version does not define is preserved, and the read survives
```gherkin
Given an event row stored directly with a name outside the reader's known set
And ordinary events for the same visitor before and after it
When that visitor's events are read in order
Then the read returns every row, including the unknown one
And the unknown name is returned as stored, never as the first known name
And the read does not fail
```

Story 15 is handed this as a written guarantee. Every read in this suite goes through a
mapper that has never met an out-of-set value.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `reports a site visit` / `opening the editor` | `POST /api/v1/analytics/events` with `event_name`, `visitor_id`, `occurrence_key` |
| `the same occurrence again` | Identical `occurrence_key` on a second request |
| `another instance` | A second session/process sharing only the database — the start's process state gone |
| `at once, interleaved at the point where…` | Latch between the read and the write, as `test_document_storage_concurrency.py` does — never two threads and hope |
| `a fresh read` | Re-read through a **new** session — never the same `AsyncSession` |
| `the stored event has no account attached` | `analytics_events.user_id IS NULL` |
| `resolve to one stored visitor` | One distinct value in the `uuid`-typed `visitor_id` column |
| `the declared type is the native identifier type` | `information_schema.data_type` = `uuid`, the assertion shape the repo already uses |
| `its braced form` / `its urn form` | `{…}` and `urn:uuid:…` spellings of one UUID |
| `characters outside the basic plane` | Astral-plane code points — N code points, 4N bytes, the fixture that separates the two units |
| `the canonical error shape` | `{error_code, message}` per `api-specs/README.md` |
| `the configured event rate limit` | The named limit/window from `endpoints.md`, fixed-window bucket keyed on `client_source()` |
| `the rate limiter's own store is unavailable` | Fault-inject the rate-limit adapter |
| `the clock fixed one tick before the window ends` | Injected `Clock` stub at the rollover boundary — never a real-time wait |
| `a distinguishable rate-limited signal` | A structured log record distinct from the swallowed-emission-failure record |
| `a frozen first-touch attribution set` | The five `utm_*` in the register body / `oauth/start` query |
| `succeeds exactly as it does for a visitor carrying no attribution at all` | Same status, same response body shape and same `error_code` set as the identical request with the `utm_*` omitted — asserted against that request, not against a literal |
| `an undecodable attribution value` | A percent-encoded cp1251 byte sequence that is not valid UTF-8 |
| `the discard is reported once` | One structured log record naming the field and the reason, carrying no value — distinct from the swallowed-emission-failure record |
| `the set of requests … accepts and refuses today` | The scenarios of `07-authorization/tests/01_API_Tests.md` §1–2 and story 16's handshake scenarios, run unmodified |
| `the geolocation configuration absent` | The named env var unset — the default, which disables resolution |
| `composed form` / `decomposed form` | NFC and NFD spellings of one string |
| `a tag with no stated priority` | `Accept-Language: en,ru;q=0.9` — absent `q` means 1.0 |
| `explicitly marked unacceptable` | `q=0`, which must never be selected |
| `a Turkish locale` | The locale the repo already parameterizes in `test_password_normalization_order.py` |
| `the generation remembers the requesting visitor` | `generations.visitor_id` column written by `RequestGeneration` |
| `an instance other than the one that received the request` | Execute `GenerateDocument` from a separate session/process |
| `two workers at once` | Interleave at the CAS window |
| `the periodic sweep` | `RequeueStaleGenerations` + `run_stale_generation_sweep` |
| `one retry key` | Repeated `Idempotency-Key` on `POST /generations/{id}/retry` |
| `answered as already applied` | The `_explain_miss` 200 branch of `SaveDocument` |
| `clocks disagree` | Two `Clock` stubs with deliberately skewed readings |
| `read in order` | Ordered by the `sequence` column |
| `a non-UTC zone` | Process `TZ` and session `TimeZone` both set away from UTC |
| `removed directly, without the eraser` | Raw `DELETE FROM accounts` — the rolling-deploy N-1 path |
| `removed through the object model` | `session.delete(account)` — the ORM relationship path, no manual detach |
| `one set-based update` | Statement count captured across two seeded volumes, asserted equal |
| `invoked with no account identified` | Eraser called with a `None` account id |
| `the event recorder rejects every write` | Fault-inject the emission port |
| `the recorder's abandonment allowance` | The named emission timeout from the spec |
| `the client's stated deadline` | The frontend's 25 s `REQUEST_TIMEOUT_MS` |
| `everything the system reported` | Captured log records, asserted on a fixed redaction token |
| `the abuse counter rows` | `oauth_rate_limits`, which this story keys on every anonymous page view |
| `a name outside the reader's known set` | Direct insert of an `event_name` the domain enumeration does not contain |
