<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Analytics Event Tracking — Infrastructure Tests

Four failure surfaces this story introduces or changes: the database the events go to, the
geolocation dependency on the registration path, the configuration that dependency and the new
bounds need in order to exist at all, and the periodic sweep whose cost this story raises.

---

## 1. The Event Store

### 1.1 A database that cannot be reached does not take the product down with it
```gherkin
Given the database is unreachable from the event recorder
When a visitor reports a site visit
Then the request is refused
When an account registers, signs in and saves a document
Then every one of those operations behaves exactly as it does today
And each failure to record is reported once, naming the event
```

### 1.2 Recording resumes by itself once the database returns
```gherkin
Given the database was unreachable and events were lost
When the database becomes reachable again
And a visitor reports a site visit
Then the event is recorded
And no operator action was required
And the events lost while it was down are not recovered
```

The last line is the point, not an omission: delivery is at-most-once by product decision.
A test asserting recovery of lost events would encode a guarantee the design refuses to make.

### 1.3 Connections are returned even when recording fails
```gherkin
Given the event recorder fails on every write
When many product operations run
Then the number of database connections in use returns to its resting level
```

### 1.4 A start that never gets its completion is detectable
```gherkin
Given a generation whose start was recorded
When its worker is aborted after the result was persisted and before any completion is recorded
And the staleness threshold elapses
Then a signal exists naming the started generation and its visitor as having no completion
And that signal is absent for a generation that completed normally
```

Emission runs after the caller's commit, so this window is real. Without a signal the only
evidence is an absence in a table nobody reads until Story 15 — and an absence is exactly what
a visitor who never generated anything also looks like.

---

### 1.4a A generation with no recorded visitor still completes, and still records
```gherkin
Given a generation row created before this feature, holding no requesting visitor
And a generation created through an instance running the previous release
When each completes
Then each completion succeeds and its document is stored
And a completed generation is recorded for each, with no visitor attached
And neither event is stored under a substitute or placeholder visitor
And no completion is lost
```

> **UNBLOCKED 2026-08-19.** `analytics_events.visitor_id` is nullable — the decision and the
> two options it beat (a sentinel visitor, an omitted event) are recorded in `endpoints.md`
> § "The five decisions the test spec was blocked on". The middle assertion is the one that
> goes red on a sentinel: a fixed UUID standing in for "unknown" satisfies the first and last
> lines while adding one enormous fake browser to every count Story 15 makes.

The browser route still requires `visitor_id` and still refuses without it (API §2.3) — the
nullability exists for the migration window on the server-emitted side, not as a relaxation of
the ingest contract.

### 1.5 The order key is wide enough for the rate this story writes at
```gherkin
Given the migration has been applied
Then the order column's declared type is the wide integer type, asserted through the schema catalogue
And its generator is declared over the same domain
Given the generator advanced past the narrow integer limit
When an event is recorded and read back in a fresh session
Then it carries that position exactly
And it orders after every earlier event
```

The load profile sets 200 requests per second sustained, one row per anonymous page view. A
32-bit order key exhausts in roughly four months, and the wrap or the constraint violation
lands on the product's busiest write path. The visitor column's type is pinned through the
schema catalogue; the order key had no equivalent assertion.

### 1.6 The stored name set is the domain catalogue, enforced by the store itself
```gherkin
Given a direct write to the event store, bypassing the route
When it stores each of the twelve catalogue names in turn
Then every one is stored
When it stores a name outside the catalogue
Then the store refuses it
```

The route accepts three names; the column's constraint is required to list all twelve so
Stories 8 and 9 need no migration. A constraint built from only the three route-accepted names
passes every scenario in every one of these files — the five server-emitted names would fail
loudly, but the four subscription names would silently block those stories at a schema level
nobody tests.

---

## 2. The Geolocation Dependency

### 2.1 A geolocation dependency that is down leaves registration working
```gherkin
Given the geolocation dependency is unavailable
When a visitor registers
Then the registration succeeds
And the account's country is unset
And the unavailability is reported
```

### 2.2 An unavailable dependency is distinguishable from an address that has no country
```gherkin
Given the geolocation dependency is unavailable
When a visitor registers
Then the unavailability is reported
Given the geolocation dependency is healthy
And a visitor registering from a private-network address
When it registers
Then the account's country is unset
And no unavailability is reported
```

Without this pair, a missing database file, an expired key and an unforwarded environment
variable all look exactly like localhost — and localhost is the *expected* result in every
development and CI run, so the failure hides precisely where it would be caught.

### 2.3 A geolocation lookup that hangs does not hold the registration open
```gherkin
Given the geolocation dependency does not answer
When a visitor registers
Then the registration answers within its normal budget
And the account's country is unset
```

### 2.4 The dependency's connections are returned, including when it fails
```gherkin
Given many registrations, half of which the geolocation dependency refuses, errors on or leaves unanswered
When all of them have completed
Then the number of open connections to the dependency returns to its resting level
And the dependency's client is not created once per registration
```

Every registration now makes an outbound call. A client constructed inside the adapter method
leaks sockets and file descriptors under this project's throughput profile, and the failure
paths are where a client is most often left unclosed. The database pool has exactly this guard
at 1.3; the new dependency had none.

### 2.5 The deployment's proxy contract matches the hop the application trusts
```gherkin
Given the monorepo and the standalone backend deployment definitions
Then the proxy layer's forwarded-header configuration is declared in each
And the hop depth the application trusts equals the number of hops that configuration adds
And a request through the deployed proxy chain resolves to the originating address rather than the proxy's
```

The address extraction is asserted elsewhere against a fabricated header chain, which passes
regardless of what the deployed proxy actually appends. This story turns that value into
durable business data on the account row, so drift writes the proxy's own address and country
onto every account with nothing going red.

**Scope, 2026-08-19.** This scenario **documents and asserts** the contract; it does not
license changing `client_source()`. That helper keys OAuth's sign-in buckets, and changing
which hop it trusts changes an existing abuse bound in a story that is not allowed to change
existing behaviour. If the assertion goes red — the deployed proxy adds a different number of
hops than the code trusts — that is a real finding to bring to the developer with the evidence,
and its fix is a change to the proxy configuration under `infra/` or a decision to alter the
helper, taken deliberately and not as a side effect of shipping analytics.

---

## 3. Configuration

### 3.1 The application starts without its geolocation configuration, and says so
```gherkin
Given the geolocation configuration is absent
When the application starts
Then it starts
And exactly one startup record names country resolution as disabled
When a visitor registers
Then the registration succeeds and the account's country reads as unset
And no resolution failure is reported
```

**Revised 2026-08-19.** This scenario previously required the boot to *fail*, the way
`JWT_SECRET` and the generation provider fail. That is the right pattern for a variable that
gates a working product and the wrong one for a variable that gates a nullable analytics
column: a story forbidden to add a failure reason to registration must not add one to the
deployment either — the running production instance would stop starting on the first upgrade
that forgot the variable.

What the fail-fast was really protecting is kept: the incident recorded in
`infra/docker-compose.yml` — four OAuth variables present in the environment file, never
forwarded to the container — must not be able to hide as silence. So «absent» is loud in the
startup log and distinguishable from «present and failing» (2.2) and from «resolved to
nothing» (2.1). What is dropped is only the process exit.

### 3.2 Every deployment declares the new configuration
```gherkin
Given the monorepo deployment definition
And the standalone backend deployment definition
Then both declare the geolocation configuration, the event rate limit and its window, and the emission abandonment allowance
And the example environment file documents every one of them, with its default and what happens when it is absent
```

The standalone backend repository is published and must boot cloned on its own
(`.claude/rules/infrastructure.md`), so a variable present in only one of the two is a
container that starts and quietly does nothing.

### 3.3 The connection pool's ceiling is read from the engine, not assumed
```gherkin
Given the application's configured engine
Then its pool size, overflow allowance and checkout wait are read from the engine itself
And those values are the ones the load scenarios use as their ceiling
Given the pool saturated
When an operation waits for a connection
Then it gives up at that engine's checkout wait, and the give-up is reported
```

**Revised 2026-08-19.** The scenario previously required this story to *set* `pool_size`,
`max_overflow` and `pool_timeout` explicitly. Story 14 does not change `session.py`: those
settings govern every existing endpoint, and re-tuning the whole application's connection
behaviour is not something an analytics story gets to do on its way past. Today's effective
values (SQLAlchemy's 5 + 10 with a 30 s blocking checkout) therefore stay in force,
**unchanged**.

What the load scenarios needed was a *knowable* ceiling, not a story-chosen one — reading it
off the engine gives them that and stays red if the real ceiling ever moves. If §2.1 or §2.2 of
`03_Load_Tests.md` shows the second checkout per action actually exhausting the pool, that is a
measurement in hand and a deliberate infra change to propose then, with the developer — not a
change this story makes pre-emptively on a prediction.

### 3.4 Every new configuration value has a named default and is reported at startup
```gherkin
Given each of the geolocation configuration, the event rate limit, its window and the emission abandonment allowance unset in turn
And then each set to a blank value in turn
When the application starts
Then each start succeeds
And the value in force is the named default, asserted against the constant rather than against a literal
And one startup record names each value in force
Given each set to a value that cannot be read as its type
When the application starts
Then each start succeeds against the named default
And the unreadable setting is reported
```

**Revised 2026-08-19**, for the reason given at 3.1. The guard that mattered was never "the
process exits" — it was "no value is in force that nobody chose". A named constant, asserted
as the effective value and printed at startup, delivers that without giving an analytics
setting the power to stop the product from booting. The blank and the unreadable cases are
both included because an env var set to `""` by a compose interpolation is the shape that
actually occurs.

### 3.5 The test environment declares its own event rate limit
```gherkin
Given the acceptance-test environment definition
Then it sets the event rate limit explicitly to a value stated for tests
And a run issuing more events than the production limit within one window from a single loopback address is not refused
And that value is not the production default inherited by omission
```

Every acceptance test originates from loopback and so shares one bucket. Without this the
suite becomes one caller and starts throwing refusals on the most-emitted event in the
product — intermittently, which is the shape that gets rerun rather than diagnosed.

---

## 4. The Recovery Sweep

### 4.1 Two overlapping sweep activations claim each generation once
```gherkin
Given a backlog of stalled generations large enough that one sweep activation outlasts its interval
When the next scheduled activation begins while the first is still running
Then each stalled generation is claimed by exactly one activation
And the number of recorded starts and completions is unchanged by the overlap
```

The existing scenarios cover several instances starting on the *same* tick. This is the other
shape: one activation still running when the next begins, which the un-limited stale query and
the un-jittered tick make reachable under a backlog. The event-count assertion elsewhere cannot
catch a double requeue, because the requeue path emits nothing by design — the claim has to be
asserted directly.

**Scope note, 2026-08-19.** This is expected to assert **existing** behaviour, not to require
new: `RequeueStaleGenerations` already claims each row through a conditional update and treats
the loser's `ConflictException` as the normal outcome, per row rather than per sweep. That
mechanism does not care whether the competing claim comes from another replica or from the
previous activation in the same process. Write the scenario, run it against today's code, and
expect green. If it goes red, the sweep has a real defect this story surfaced — report it, do
not fix it inside an analytics work unit.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the database is unreachable from the event recorder` | Fault-inject the emission adapter's session factory |
| `each failure to record is reported once` | One structured log record carrying `event_name` and `visitor_id` as fields |
| `connections in use returns to its resting level` | SQLAlchemy pool `checkedout()` before and after the run |
| `a signal exists naming the started generation` | A structured record distinguishable from the swallowed-emission-failure record |
| `the geolocation dependency is unavailable` | Stub `GeoLocationPort` to raise |
| `country resolution is disabled` | The named env var unset — the default; the port is wired to a no-op that resolves nothing and reports nothing |
| `the named default` | The module-level constant the setting falls back to, asserted by importing it — never a literal repeated in the test |
| `read from the engine itself` | The configured `AsyncEngine`'s pool attributes, not a value this story sets |
| `no visitor attached` | `analytics_events.visitor_id IS NULL` |
| `a substitute or placeholder visitor` | Any fixed non-NULL UUID standing in for "unknown" |
| `does not answer` | Stub the port to hang past its configured timeout |
| `no unavailability is reported` | Assert the absence of the specific failure signal, not the absence of all logging |
| `open connections to the dependency` | The HTTP client's own connection-pool gauge, sampled before and after |
| `the proxy layer's forwarded-header configuration` | The nginx/proxy config under `infra/`, read as the source of the trusted hop depth |
| `the monorepo deployment definition` | `infra/docker-compose.yml` |
| `the standalone backend deployment definition` | `backend/docker-compose.yml` + `backend/Dockerfile` |
| `the example environment file` | `backend/.env.example`, covered by `test_env_example_documents_every_variable.py` |
| `the acceptance-test environment definition` | The environment the acceptance suite boots the backend with |
| `claimed by exactly one activation` | A leased or conditional update — rows affected = 0 for the loser, never a plain list-then-requeue |
