# Story 14: Analytics Event Tracking — Backend Progress

Owns: Backend, Integration, Security, Load and Infrastructure Scenarios (acceptance steps
stay inline per scenario — they aren't a separable layer). Narrative/decisions/Spec
checklist live in `progress.md`; `ProductSpecification/stories.md` is the cross-file
rollup. Extended scenarios (`tests/extended/`) are not bootstrapped here — they are folded
in once the critical file they extend is green.

Implementation order (per `01_API_Tests.md`): the ingest route and its identity rules
(§1–§2) → the payload and the fields a client may not choose (§3–§4) → idempotency and
rate limiting (§5–§6) → the server-emitted events on the existing product routes (§7–§9)
→ ordering, erasure and the fail-open guarantee (§10–§13). Integration, Security, Load and
Infrastructure follow, in that order.

## Backend Scenarios (01_API_Tests.md)

### 1.1 An event with no token is recorded as anonymous
- [x] red-acceptance — acceptance suite `tests/backend/analytics/`, with the story's first
  direct Postgres probe (`clients/database/analytics_event_probe.py`, precedent approved
  2026-08-19 — see `progress.md` § Decisions). Predicted and actual failure matched on the
  first run: `UndefinedTableError: relation "analytics_events" does not exist`, raised in
  the given-phase before any assertion. `/test-review` re-scoped the row count to the
  visitor rather than to `visitor_id AND occurrence_key` (the narrow scope could only ever
  return rows that already carried the expected key, so a rewritten or NULL key read as
  "nothing was written"), and selected `occurrence_key` back to be asserted.
  Note for green: the probe names `occurrence_key` in its SELECT list, so a migration that
  picks a different column name fails as `UndefinedColumnError` naming it.
- [x] design — hazard scan ran all 8 catalogue groups (46 GAPs). Shape folded per
  `decisions/analytics-ingest-shape-decision.md`: `save_new -> SaveOutcome` with the
  collapse decided by `ON CONFLICT` rather than a prior read; a PARTIAL unique index
  `WHERE occurrence_key IS NOT NULL` (a plain UNIQUE is void on NULLs, and
  `NULLS NOT DISTINCT` would collapse every server-emitted event for one visitor into a
  single row); a `degraded` column; `sequence` narrowed to a stable sort key, explicitly
  not a gap-safe cursor; `user_id` FK `ON DELETE SET NULL` with analytics rows
  deliberately surviving account erasure. Limiter, payload-validation and failure-log
  slots land as SHAPE only — each guard lands with its own scenario (3.x, 6.x, Infra 1.1).
  Note for green: `POST /api/v1/analytics/events` turns
  `application/tests/test_every_route_states_whether_it_needs_a_token.py` red until it is
  added to `_DELIBERATELY_PUBLIC` with a reason; and value objects must guard
  `isinstance(raw, str)` first, since `uuid.UUID` raises `AttributeError`/`TypeError`
  on a non-string, not `ValueError`.
- [x] red-usecase — `usecase/tests/analytics/test_record_analytics_event_usecase.py` with
  `AnalyticsIngestStatements` and a functional `FakeAnalyticsEventRepository`. Predicted
  and actual failure matched on the first run: bare `NotImplementedError` at
  `usecase/src/analytics/record_analytics_event.py:45`, raised in the when-phase before
  any assertion, so the fake is never handed an event. A domain field gate kept only the
  five fields a 1.1 line actually reads — `payload`, `degraded`, `id` and `sequence` are
  deliberately NOT on the entity (each has its own later scenario; `sequence` is
  database-assigned and the ADR forbids modelling it at all). `/test-review` replaced
  three per-field assertions with one structural comparison against a fully-constructed
  expected event: strictly stronger (it now also pins `user_id` and `event_time` inside
  the "event is recorded" claim) and it makes the field gate self-enforcing — the next
  field added to the entity turns 1.1 red until it states what an anonymous visit stores.
  Note for green: `execute` needs no validation branch yet (nothing in 1.1 asserts a
  refusal) and must NOT branch on `SaveOutcome` — only `STORED` is a path at 1.1.
- [x] green-usecase — `execute` replaced its `NotImplementedError` with the five-line happy
  path: construct `AnalyticsEvent`, parse both identifiers with `UUID(...)` from the wire
  strings, pass `user_id` through unread, stamp `event_time` from the injected `Clock`,
  `save_new`, `commit`. No validation branch, no branch on `SaveOutcome`, no
  `try`/`rollback_quietly`, no limiter or failure-log slots — each is absent by design,
  owned by 2.x/3.x, `extended/01` §3.1 (corrected from "5.x" in `red-adapter db` —
  §5.1–§5.6 hold no conflicting-name scenario), §12–§13 and 6.x/Infra 1.1
  respectively. Tests: 1/1 target,
  298/298 `backend/usecase`. `/test-coverage usecase --focus`: 14/14 lines, 0/0 branches
  on the touched file — the deliberate omissions read as *absent* branches rather than
  cold ones, which is why the number is 0/0 and not 2/6; no gaps, no steps inserted.
  Environment note (ruled on, not a result of this change): the Docker daemon is down on
  this host so `adapters/db` tests skip by prerequisite, and
  `rendering/tests/rendering/test_weasyprint_pdf_renderer.py` fails to collect on a
  missing GTK system library. `backend/adapters/rendering` has no working-tree change and
  a usecase test that only uses fakes cannot reach either — so the full-suite run was
  narrowed rather than claimed clean.
  Note for adapters-discovery: `UUID(visitor_id)` raises on a malformed string today and
  nothing drives it. That is 2.3's refusal to specify, not a gap here — and per the design
  note the guard must test `isinstance(raw, str)` first, since a non-string raises
  `AttributeError`/`TypeError`, not `ValueError`.
- [x] adapters-discovery — **Check 1 (ports):** `AnalyticsEventRepository` has no
  implementation anywhere — no `analytics` under `adapters/db/src/access/` or `model/`, and
  no migration creates `analytics_events` → `red-adapter db` / `green-adapter db`. `Clock`
  and `UnitOfWork` are `[S]`: both already implemented and already exercised by the sibling
  usecases this one was modelled on. The checklist's write-here-read-there rule does **not**
  apply and is not being dodged — the port is write-only by design (`endpoints.md`: "reading
  is Story 15"), so there is no reader usecase and no second port to read through. The
  adapter test asserts through a direct SQL read, the same way the acceptance probe does,
  because no read port exists to assert through.
  **Check 2 (exceptions):** `[S]` — the 1.1 path raises no domain exception at all (no
  validation branch, by design). `UUID(...)` can raise `ValueError`/`TypeError`, but that is
  a stdlib parse failure on the 2.3 path, not a domain exception 1.1 can reach, and mapping
  it is 2.3's work.
  **Check 3 (response shape):** `POST /api/v1/analytics/events` is registered on no router —
  the route does not exist → `red-adapter rest` / `green-adapter rest`. Contract is `204 No
  Content`, no body. Note the acceptance test deliberately never asserts the status (the
  claim is the stored row, not the answer), so the route existing is necessary but the test
  will not catch a wrong success code here — §5.x is where a status becomes an assertion.
  **Carried into `green-adapter db` — the outcome distinction must not be designed away.**
  The ADR's `INSERT ... ON CONFLICT (visitor_id, occurrence_key) DO NOTHING RETURNING id`
  returns zero rows for `ALREADY_RECORDED` *and* for `CONFLICTING_NAME`; telling them apart
  needs a follow-up read of the stored row's `event_name`. 1.1 exercises only `STORED`, so
  the TDD-minimal adapter would write `no row → ALREADY_RECORDED` and strand the third enum
  member permanently. It is legitimate to defer the branch (it is code, not schema — unlike
  the table itself, adding it later costs no migration on a hot table), but **not** to
  foreclose it: `green-adapter db` must leave the zero-row case an explicit, single, named
  decision point rather than a hardcoded return.
  **Ownership correction (verified 2026-08-20, premortem finding on `538cb46c`).** The
  `SaveOutcome` docstring, `record_analytics_event.execute`'s docstring and this file's
  `green-usecase` note all say the 204-vs-409 branch lands at "§5.x". It does not:
  `01_API_Tests.md` §5.1–§5.6 contain no conflicting-name scenario (§5.3 is a *malformed*
  key). The only scenario asserting it is `tests/extended/01_API_Tests_Extended.md` §3.1,
  which the header of this file excludes until the critical file is green — while
  `endpoints.md` §2 mandates `409 OCCURRENCE_KEY_CONFLICT`. So the branch currently has no
  bootstrapped owner. Correct the three "§5.x" pointers to `extended/01` §3.1 in the next
  work unit that touches those files (`red-adapter db`), and fold extended §3.1 in when §5
  goes green rather than leaving the 409 to be discovered by Story 15.
- [x] red-adapter db — SQLAlchemy model + one Alembic migration creating the whole
  `analytics_events` table per the ADR (partial unique index `WHERE occurrence_key IS NOT
  NULL`, `degraded BOOLEAN NOT NULL DEFAULT false`, `sequence BIGINT GENERATED ALWAYS AS
  IDENTITY`, `user_id` FK `ON DELETE SET NULL`, twelve-name CHECK), and `save_new` via
  `ON CONFLICT ... DO NOTHING RETURNING id`. The whole table lands at once deliberately —
  the ADR rejects the TDD-minimal split because both the unique index and `sequence` would
  otherwise become migrations on the product's busiest write path.
  Note: `SqlAlchemyAccountEraser`'s hand-maintained docstring gains `analytics_events` and
  its `SET NULL` action — the ADR calls this table a deliberate departure from the repo's
  `NO ACTION`-plus-ordered-delete convention.
  **Done.** Test `access/analytics/test_analytics_event_storage.py` (41 lines) +
  `statements/analytics_event_storage_statements.py`, fixture registered in
  `engine_scoped_fixtures.py` (`_EXPECTED_FIXTURES` 9 → 10). The red is the adapter's
  absence, not the schema's: a `SqlAlchemyAnalyticsEventRepository.save_new` stub raises
  before the fresh read ever runs, so the missing table is never what fails. Predicted and
  actual matched on the first run (bare `NotImplementedError` at
  `access/analytics/analytics_event_storage.py:36`, when-phase, before any assertion;
  76 passed + 1 failed → 76 passed + 1 skipped after marking).
  `/test-review` found the strictest assertion in the file was blind to a whole class of
  error: `REPORTED_AT` had zero microseconds, so a `TIMESTAMP(0)` column truncating every
  real event to the second would carry `09:30:00.000000` back unchanged and pass. Now
  `09:30:12.345678` — same single structural assertion, but it discriminates a
  full-precision column from a truncating one. The AcceptanceCriteria ask for exactly that
  guard and no scenario in the story owned it (`grep -rn microsecond tests/` returned
  nothing).
  The three "§5.x" ownership pointers were corrected here to `extended/01` §3.1, per the
  instruction left by `adapters-discovery`. Comment-only, verified inert against 754
  usecase+domain tests.
  Note for green: `_SERVER_NOW` in `usecase/tests/statements/analytics_ingest_statements.py`
  still reads `09:30` flat, so the two layers no longer name one instant. Harmless (each
  test asserts against its own constant) but worth aligning when something else touches
  that file.
- [x] green-adapter db — must also (a) add `analytics_events` to `TRUNCATE_ALL` in
  `statements/database_cleanup.py` with the migration — it cannot be added earlier without
  turning all 76 db tests red against a non-existent relation, and the module's rule is
  that the list enumerates every table by hand; and (b) add `analytics_events` + its
  `SET NULL` action to `SqlAlchemyAccountEraser`'s hand-maintained docstring, deferred
  from `red-adapter db` because documenting an FK on a table that does not exist yet
  would have been false.
  The zero-row decision point stays on you, not on the test:
  `assert_the_store_reported_a_new_row` pins only `STORED`, so nothing here stops a
  hardcoded `no row → ALREADY_RECORDED` stranding `CONFLICTING_NAME`.
  **Done.** `AnalyticsEventModel` (101 lines), the migration `c5d6e7f8a9b0` creating the
  whole table, `save_new` via `ON CONFLICT ... DO NOTHING RETURNING id`, and the domain
  catalogue `domain/src/analytics/event_names.py` the CHECK constraint is *iterated* from.
  Both (a) and (b) landed; `migrations/env.py` also gained the model import, without which
  autogenerate would propose dropping the table it just created. The skip marker was the
  only test change. Tests: 77 passed (76 + the newly enabled one), 0 failed; domain 456,
  usecase 298, application 66, all unchanged.
  The zero-row case was NOT hardcoded away — it is `_what_the_conflicting_row_means()`, one
  named method whose docstring records that `DO NOTHING` cannot distinguish
  `ALREADY_RECORDED` from `CONFLICTING_NAME` and that the follow-up read lands there.
  `/test-coverage db --focus`: model, eraser and `event_names` 100%; the storage adapter
  16/18 lines and 1/2 branches — the three cold lines are exactly that zero-row cluster.
  Ruled as §5.1's claim, not a 1.1 gap (1.1's Gherkin ends at one insert), so no steps were
  inserted. Coverage also noted the partial index is already load-bearing at 1.1: Postgres
  refuses an `ON CONFLICT` spec it cannot match a unique index to at plan time, so a wrong
  `index_elements`/`index_where` fails the *non*-conflicting insert too.
- [~] red-adapter rest — `POST /api/v1/analytics/events`, `204 No Content`, no body.
  Request DTO fields typed permissively **and defaulted** per the ADR, so a bad value
  reaches the domain and returns the canonical 400 rather than Pydantic's 422 echoing the
  rejected input back on the product's only tokenless route.
- [ ] green-adapter rest — also adds `("POST", "/api/v1/analytics/events")` to
  `_DELIBERATELY_PUBLIC` with its reason in
  `application/tests/test_every_route_states_whether_it_needs_a_token.py`, which goes red
  the moment the route is registered. That is the deliberate reviewable line, not an
  obstacle to route around.
- [ ] green-acceptance

### 1.2 An event from a signed-in caller is attributed to that account
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.3 A present but unusable token is refused, never downgraded to anonymous
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.1 Only browser-origin event names are accepted
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.2 Server-only and subscription event names are refused from a client
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.3 A malformed visitor identifier is refused and never stored raw
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.4 The same visitor written in any accepted form is one visitor
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.1 A payload at the size limit is accepted and one byte over is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.2 A payload that is small but deeply nested or wide is refused, not crashed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.3 A payload containing characters the store cannot hold is refused cleanly
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.4 An oversized body is refused on bytes read, not on the declared length
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.5 The payload limit is measured in bytes, not in characters
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.6 A payload survives store and read with its values unchanged
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 4.1 A client cannot choose the account an event belongs to
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 4.2 A client cannot choose when an event happened
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 4.3 A client cannot choose an event's identity or its position in the order
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 4.4 A field this version does not know is ignored, not refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.1 One occurrence reported twice is recorded once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery — **do not mark db `[S]` on the grounds that the port is already
  implemented** (coverage finding at 1.1 `green-adapter db`, 2026-08-20). By this point
  `SqlAlchemyAnalyticsEventRepository` exists, which is the usual reason Check 1 skips the
  layer — but the port existing is not the same as its *collapse* behavior being proven.
  `save_new`'s zero-row path (`if inserted_id is None` → `_what_the_conflicting_row_means`)
  is cold code that only §5.1 can reach. Skip db here and the partial-index collapse is
  never asserted below acceptance for the rest of the story.
- [ ] green-acceptance

### 5.2 Two distinct occurrences from one visitor are both recorded
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.3 A missing or malformed occurrence key is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.4 One occurrence reported to two instances is recorded once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.5 One occurrence reported twice at the same instant is recorded once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.6 One occurrence key in two letter cases is one occurrence
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 6.1 A caller at the rate limit is served and one request over is refused
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 6.2 Analytics traffic cannot exhaust an account's sign-in budget
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 6.3 A rate limiter that cannot answer refuses the event
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 6.4 The rate limit is one budget across every instance
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 6.5 The window admits exactly at the rollover instant
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 6.6 A rate limiter that does not answer does not hold the request open
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 6.7 Events refused by the limiter are counted, not merely dropped
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.1 Registration stores the caller's technical context and first-touch attribution
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.2 The context survives the next write to the same account
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.3 An account created before this feature still reads
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.4 The country of an address that cannot be located is unset
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.5 Attribution values are normalized before the bound, and dropped over it
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.5a Attribution never changes the registration's answer
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.6 The same attribution written two ways is stored one way
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.7 A client cannot supply its own address, country, device or verification state
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.8 Text the store cannot hold is dropped at registration, never stored mangled
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.9 An explicitly empty attribution value and an omitted one are the same stored state
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.10 The highest-priority language tag wins, at every edge of the priority list
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.11 An unusable language header stores nothing, never a default
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.12 The attribution bound is measured in characters, not bytes
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 7.13 The language tag is canonicalized under an invariant locale
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 8.1 Confirming a code records the registration once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 8.2 Confirming the same code twice records one registration
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 8.3 Two simultaneous confirmations record one registration
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 8.4 A first sign-in through a provider records both a registration and a sign-in
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 8.5 A later sign-in through the same provider records only a sign-in
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 8.6 Attribution frozen in the browser reaches a provider-created account
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 8.7 A pair whose second emission fails keeps the first and re-attempts nothing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.1 Requesting a generation records a start and remembers the visitor
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.2 A completed generation is recorded with the requesting visitor, from any instance
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.3 A generation completed twice records one completion
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.4 Recovering a stalled generation records no new start
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.5 A retried generation records a new start only when a generation was created
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.6 Saving a document records a save
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.7 A save that persisted nothing records nothing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.8 A generation that already failed records no completion
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.9 A generation that already completed records nothing further
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.10 The requesting visitor survives a requeue
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 9.11 One generation failing mid-sweep neither discards the earlier recoveries nor blocks the later ones
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 10.1 Events for one visitor are ordered by their position, not their time
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 10.2 Two events sharing a moment have a stable, repeatable order
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 10.3 A recorded moment keeps its precision and its zone
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 10.4 A moment recorded under a non-UTC server timezone is the same instant
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.1 Deleting an account detaches its events and keeps them
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.2 Deleting one account leaves every other account's events untouched
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.3 Deleting an account with no events changes nothing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.4 Removing an account row outside the eraser does not fail on its events
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.5 A deletion that fails part-way leaves the events attached
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.6 An event arriving during a deletion cannot break it
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.7 Detaching an account's events costs the same at any volume
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.8 An erasure with no account to scope to changes nothing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.9 Removing an account through the object model detaches its events, never deletes them
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 11.10 An event reported with a deleted account's token is refused, not silently attributed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.1 A failing recorder changes no product outcome
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.2 A failing recorder is not silent
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.3 A hanging recorder does not hold the caller
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.4 A product operation that rolls back records no event
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.5 A recorded event is readable by another connection once its call has answered
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.6 A confirmation that rolls back records no registration
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.7 A recorder that answers just inside its allowance still records
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.8 Every slow hop on one request still fits inside the caller's deadline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.9 A reported event is readable by another connection once its call has answered
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.10 The two extended auth routes answer exactly as they did before this story
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 12.11 A missing geolocation configuration is not a failed boot
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 13.1 Personal data lives on the account and nowhere else
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 13.2 A refusal never echoes what was rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 13.3 A stored event name this version does not define is preserved, and the read survives
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Integration Scenarios (06_Integration_Tests.md)

### 1.1 A located address is stored as its country
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.2 Every failure mode leaves registration whole and the country unset
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.3 A failing dependency is asked once, not repeatedly
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.4 A dependency that does not answer is abandoned, not waited on
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.5 The address the dependency is asked about is the caller's, not a proxy's
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.1 Attribution carried into the handshake reaches the created account
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.2 Attribution parked on one instance is read back by another
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.3 The campaign parameters are never handed to the provider
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.4 A first provider sign-in records both events; a later one records only the sign-in
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.5 A callback arriving just inside the handshake's lifetime keeps the attribution
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.6 A provider-created account carries the same technical context as a registered one
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Security Scenarios (05_Security_Tests.md)

### 1.1 A client cannot fabricate the events the business is measured by
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.2 A signed-in caller cannot attach its events to another account
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.3 A caller cannot rewrite another visitor's history
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.4 A resource named in a payload confers nothing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.1 Server-owned fields cannot be set from the event body
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.2 Server-owned fields cannot be set from the registration body
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.3 The handshake binds only the five campaign parameters
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.1 Hostile text in any stored field is stored, not executed, and never reflected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.2 Hostile text in a payload is stored, not transformed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.3 A refusal never reflects what it rejected
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.4 A refusal caused by an internal failure discloses nothing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.5 Hostile text cannot forge a log entry
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.6 Campaign parameters cannot forge a redirect or a header
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 4.1 An anonymous flood is bounded and fails closed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 4.2 Oversized and malformed bodies are refused before they are absorbed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 4.3 Oversized and pathological headers are bounded, not parsed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.1 Personal data is stored in exactly one place
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.2 The abuse counters do not store the address in recoverable form
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.3 Deleting an account removes its personal data and bounds what is left
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.4 The abuse counters do not become a permanent visitor log
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.5 Pruning elapsed counters leaves live counters and the sign-in counters alone
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.6 A dependency's credential never reaches a log or a response
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 5.7 A presented token never reaches a log or a response
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Load Scenarios (03_Load_Tests.md)

### 1.1 The events endpoint sustains the anonymous visitor rate
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.1 Product endpoints hold their rate with emission switched on
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.2 A recorder that never answers does not slow the operations it observes
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.1 [S] The recovery sweep reads a bounded batch, never the whole backlog — *out of scope for Story 14, see task 7*
- [S] out of scope for Story 14 — decided 2026-08-19, see `progress.md`
      § Decisions and `tasks/7-refactoring-bound-stale-generation-sweep/`.
      `GenerationStorage.list_stale` is NOT to be changed by this story.

## Infrastructure Scenarios (04_Infrastructure_Tests.md)

### 1.1 A database that cannot be reached does not take the product down with it
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.2 Recording resumes by itself once the database returns
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.3 Connections are returned even when recording fails
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.4 A start that never gets its completion is detectable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.4a A generation with no recorded visitor still completes, and still records
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.5 The order key is wide enough for the rate this story writes at
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 1.6 The stored name set is the domain catalogue, enforced by the store itself
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.1 A geolocation dependency that is down leaves registration working
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.2 An unavailable dependency is distinguishable from an address that has no country
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.3 A geolocation lookup that hangs does not hold the registration open
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.4 The dependency's connections are returned, including when it fails
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 2.5 The deployment's proxy contract matches the hop the application trusts
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.1 The application starts without its geolocation configuration, and says so
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.2 Every deployment declares the new configuration
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.3 The connection pool's ceiling is read from the engine, not assumed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.4 Every new configuration value has a named default and is reported at startup
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 3.5 The test environment declares its own event rate limit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### 4.1 Two overlapping sweep activations claim each generation once
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

