# Analytics Event Tracking — Folded Hazard-Scan Guards

> **Read the Governing Decision in `14_AnalyticsEventTracking.md` first.** It was agreed with
> the developer on 2026-08-19, after these guards were folded, and it overrides any guard here
> that would change an existing user scenario, add a refusal reason to an existing operation,
> or change an existing status code. Three guards were rewritten under it rather than deleted —
> over-bound attribution, the legacy-charset attribution value, and the GeoIP boot contract —
> and each rewrite is marked **(FOA)** in place.

Every guard below came from the Phase-4 hazard scan (groups 1–8, 2026-08-16) and is written
so a downstream test can go red on it. Grouped by area, not by catalogue group — several are
one guard closing a seam two or three passes found from different sides. The scan record,
including the group set covered and each GAP's disposition, is in
`tests/00_Hazard_Scan_Record.md`.

## Ordering, the clock, and the total order

Three passes wanted three different things from `event_time` — microsecond-exact equality for
the OAuth pair (g1), a single skew-proof clock across instances (g3), and an injectable clock
so tests can fix time (g7). They are reconciled by splitting the two jobs the timestamp was
being asked to do: **`event_time` records when, `sequence` decides order.**

- `event_time` comes from the injected `Clock`, the port eight usecases already take. A test
  with the clock fixed asserts the persisted value equals that instant exactly, and a re-read
  in a **separate DB session** returns it with `tzinfo` present — `DateTime(timezone=True)`
  accepts a naive datetime silently.
- A timestamp with non-zero microseconds survives store → read unchanged; the column does not
  truncate to seconds.
- `CompleteOAuthCallback` reads the clock **once** and passes that instant to both emissions:
  the two rows' `event_time` are byte-equal, not "within a second".
- `sequence` is database-assigned and monotonic. Two events for one `visitor_id` written from
  two different sessions come back in causal order **even when their `event_time` values are
  equal or inverted** — the guard is a test that stores the pair with deliberately skewed
  clock readings and asserts the stored order still places the earlier cause first.
- `GENERATION_STARTED` (request instance) and `GENERATION_COMPLETED` (sweep instance, minutes
  later) are ordered by `sequence`, never by comparing two instances' clocks.
- Reading twice returns two rows sharing an `event_time` in the same stable order — the
  tiebreaker Story 15's paging needs, put in the schema now while it is cheap.

## Emission is bound to the transition, never to the 200

The single rule behind six findings across four passes. Every one of these paths returns
success **without** having performed a write, and an emitter hung on "the call returned"
inflates the funnel.

- **Verify replay.** `POST /auth/verify` twice with the same valid code → exactly one
  `REGISTRATION_COMPLETED`; the second call still answers 200. `verify_account.py` discards
  the CAS return value and its own comment names this exact future hazard ("A future verify
  side-effect … must re-read the rows"), so the emitter must be conditional on the CAS win.
- **Concurrent verify.** Two simultaneous verifies of one unverified account → one event.
- **Autosave replay.** `save_document.py::_explain_miss` answers 200 for a save that already
  landed and persisted nothing, and `autosaveRetryPolicy.ts` retries up to four times on
  timeout/5xx. Driving that branch produces **zero** additional `DOCUMENT_SAVED`; the event is
  bound to `save_content_if_version_matches` returning a row.
- **Generation CAS.** Two `GenerateDocument` runs for one generation interleaved at the CAS
  window → exactly one `GENERATION_COMPLETED`, belonging to the run whose content persisted.
- **Retry.** `POST /generations/{id}/retry` twice with one `Idempotency-Key` → exactly one
  `GENERATION_STARTED` (the `created=False` branch emits nothing); a fresh key → one more.
- **Sweep.** With K stale generations and M replicas sweeping the same tick → exactly K
  events, not M×K, and the requeue path itself emits nothing.
- **Terminal states.** A generation already `failed` that later completes emits no
  `GENERATION_COMPLETED`; the domain's setters are bare assignments with no legality check, so
  this cannot be assumed from the state machine.

## Transaction boundary and session ownership

- **The pattern the spec points at is the trap.** `oauth_rate_limit_storage` commits the
  *request's* session — safe for a guard that runs before any business write, fatal for an
  emitter that runs after one. Guard: force the caller's own commit to fail after the emission
  point, once for `SaveDocument` and once for `RegisterUser`, and assert **no analytics row**
  and **no partially-committed business row**.
- Emission happens after commit, so a phantom event for a rolled-back operation is impossible;
  the inverse is accepted loss by product decision.
- **Read-after-write contract.** After `/auth/verify` answers 200, `REGISTRATION_COMPLETED` is
  readable on a **different connection**; after the ingest endpoint answers, the row is
  readable on a different connection. Without this the "stored" assertions are satisfiable by
  a flaky test.
- **Eraser atomicity.** Force the final `DELETE FROM accounts` to fail after the events were
  nulled; assert the nulling rolled back — no events orphaned at `user_id IS NULL` beside an
  account that still exists.
- **Session leak.** Drive the emission path many times **including the failure branch** and
  assert checked-out connections return to baseline. The swallow sits outside the acquisition,
  never inside it, or the pool drains silently under load.

## The public endpoint

- **The accepted set narrows to what a client may legitimately send:** `SITE_VISITED`,
  `REGISTRATION_STARTED`, `EDITOR_OPENED`. Posting each of the four subscription names, and
  each of the five server-only names, with no token → 400, nothing stored. Without this,
  "no client is allowed to send them" is a comment, and anyone can `curl`
  `SUBSCRIPTION_ACTIVATED` into the table Story 15 computes revenue from.
- **Bad token is not silent anonymity.** Three tests: no header → stored with `user_id IS
  NULL`; valid token → stored with the token's subject; garbage / expired / refresh-typed →
  401, nothing stored.
- **`visitor_id` is untrusted telemetry.** Stated in writing so Story 15 cannot key a security,
  billing or entitlement decision on it. Testable half: an authenticated caller posting a
  `visitor_id` minted by another browser stores the **token's** `user_id`, never one inferred
  from the visitor, and mutates no existing row.
- **Server-owned fields cannot be over-bound.** Bodies carrying `user_id`, `event_time`, `id`
  and `sequence` are each asserted to have no effect on the persisted row. Pydantic v2 ignores
  extra keys silently, so an over-wide DTO looks identical to a correct one on the happy path.
- **Register's writable allow-list** is exactly the five `utm_*`. A register body carrying
  `country`, `device_type`, `os`, `ip`, `is_verified`, `failed_attempt_count` or `created_at`
  leaves every one of those columns at its server-derived or default value.
- **Rate limiter fails closed.** Drive the limiter's own store into an error and assert the
  event is refused, not accepted. The story-wide "swallow analytics failures" rule pushes the
  naive implementation the other way, and this is the only volume bound on the hottest path.
- **Bucket key space is separate from OAuth's**, or analytics traffic exhausts an IP's login
  budget. Asserted by driving analytics traffic to the limit and confirming a login from the
  same IP still succeeds.
- **Error bodies disclose nothing and echo nothing.** For each failure family — unknown name,
  malformed `visitor_id`, oversized body, rate-limited, storage down — the body matches the
  canonical `{error_code, message}` shape with no stack-trace marker, SQL keyword, internal
  class name, file path, or echoed input. Posting `event_name` = `<script>alert(1)</script>`
  asserts a 400, not FastAPI's 422 envelope, which echoes the rejected value back; the repo
  already documented that trap in `update_profile_request_dto.py`.

## Bounds — every one a number, with its unit

The repo measures size in two units already (transport counts bytes off `Content-Length`,
every domain cap counts code points), so an unnamed bound is an ambiguous bound.

- Each of request body, `payload`, `event_name`, occurrence key, each `utm_*` and the device
  language tag carries a **named numeric limit and a stated unit**. Each bound is tested at
  exactly the limit (accepted) and at limit+1.
- **The two halves of that sentence differ by route (FOA).** On the new ingest endpoint,
  limit+1 is *rejected* with its documented `error_code`. On `/auth/register` and
  `/auth/oauth/{provider}/start`, limit+1 is *dropped*: the attribution set is discarded whole,
  the account is created, the sign-in completes, and the response is byte-identical to the one
  the same request gets today. An over-bound `utm_campaign` that refuses a registration is the
  single defect this story is most likely to ship, and it is forbidden.
- Text bounds use a fixture that **differs in the two representations** — astral-plane emoji,
  N code points and 4N bytes — sitting on one side of the bound in code points and the other
  in bytes. An ASCII fixture can never go red on a swapped unit.
- **The chunked-body bypass.** The same oversized body sent with no `Content-Length` is
  refused after the cap's worth of bytes is read; the process never buffers the whole body.
  `avatar_router.py` records this scar verbatim.
- **Depth and breadth, not just size.** A payload nested D levels deep, and one with tens of
  thousands of keys, both **under** the byte cap, answer 400 within a wall-clock bound — never
  a `RecursionError` 500, never a stall.
- The rate limit names a request count and a window, tested at N (accepted), N+1 (refused),
  and the first request of the next window (accepted), with the clock fixed at the rollover.
- **The test environment sets its own limit by contract.** Acceptance tests all originate from
  loopback, so they share one bucket and would otherwise throw nondeterministic 429s on the
  product's most-emitted event.

## Text: normalization and canonical form

- `visitor_id` is a native `uuid` column — asserted through `information_schema.data_type`, the
  assertion shape the repo already uses. Upper-case, lower-case and any accepted alternate
  form resolve to one stored value and one visitor. Stored as text, `A1B2…` and `a1b2…` would
  be one UUID and two visitors, and every funnel would double-count silently.
- `utm_*` are NFC-normalized before the bound, with the order pinned the way
  `test_password_normalization_order.py` pins it: a value that exceeds the bound raw but fits
  after NFC gets the stated outcome. NFC and NFD forms of one campaign name store identically,
  or Story 15 splits one campaign in two.
- Over-bound `utm_*` are **dropped, not truncated, and never rejected (FOA)**. Truncation is
  still forbidden — it removes the mid-grapheme cut question and a truncated campaign name is a
  wrong campaign name — but the response to an over-bound value is the one the request would
  have got before this story existed. Because attribution is one set (`B2`), the other four
  values go with it: an account's attribution is always internally consistent, never a partial
  set that no marketing link ever produced.
- `Accept-Language`: `ru-RU`, `ru-ru` and `RU-RU` store one canonical value; a multi-tag q-list
  asserts exactly which tag wins; the parse is locale-invariant, tested under the Turkish
  locale the repo already parameterizes.
- Device type and OS map onto a closed domain taxonomy from a fixed table of real User-Agent
  strings; absent, garbage and out-of-taxonomy UAs → NULL, never the parser's catch-all
  bucket, which would silently bucket unknowns as "Desktop"/"Other" and fragment on upgrade.
- `payload` containing ` ` or a lone surrogate → 400 in the canonical envelope, nothing
  stored. Postgres `jsonb` rejects the first outright and the second raises `UnicodeEncodeError`
  on encode; both otherwise turn a well-formed hostile request into a 500 or a silent loss.

## Registration context: the write path and the rows that already exist

- **The killer, and the reason this is its own section.** The registration round-trip test is
  not enough. `save()`'s update branch and `to_domain` each enumerate columns by hand, and
  `/auth/verify` re-saves the account through that branch **immediately after registration**.
  A column present in one list and missing from the other writes NULL over the UTM set at the
  moment of verification — for every email-registered user — while the registration test stays
  green. Guard: register with a full set, then perform a second save (verify, then a profile
  rename, then a failed login), re-read in a new session after each, and assert all eleven
  values are byte-identical to what registration stored.
- **Legacy rows.** Insert an `accounts` row with the eleven columns NULL, read it through
  `find_by_id` **and** `GET /api/v1/auth/me`: a valid `Account` and a 200, not a validation
  error and not a placeholder. Every account registered before this migration is that row.
- The round-trip fixture is Cyrillic plus an astral-plane emoji, asserted byte-exact end to
  end — browser → `POST /auth/register` → DB → re-read.
- **A non-UTF-8 percent-encoded UTM value (a cp1251 marketing link) is not stored (FOA).** The
  decision, taken by the product owner on 2026-08-17 and confirmed 2026-08-19: mojibake must
  never be frozen as an account's permanent attribution, and an unreadable marketing link must
  never cost the visitor their registration. So the browser does not freeze it, the server does
  not store it, the set is discarded whole, and the registration or sign-in completes exactly
  as it would with no UTM at all. A later visit carrying a readable link can still become the
  first touch.
- `utm_*` are stored byte-identical to what was sent (after normalization) — including
  `=cmd|'/c calc'!A1` and `<script>alert(1)</script>` — proving no premature input-encoding
  that would defeat the sink-side escape Story 15 owes.

## Deletion and erasure

- **`ON DELETE SET NULL` on the FK**, agreeing with the eraser's explicit step. Without it the
  default is `NO ACTION`, and during a rolling deploy an N-1 replica whose eraser knows nothing
  about analytics answers 500 on `POST /auth/me/deletion` and deletes nothing, for every
  account that has an event. Guard: delete an `accounts` row by raw SQL, bypassing the eraser,
  and assert the account is gone, its events survive with `user_id IS NULL`, and no
  `IntegrityError`.
- **Blast radius.** With account A's events, account B's events and anonymous events present,
  erasing A changes **exactly** A's rows: B's `user_id` unchanged, anonymous rows unchanged,
  total row count unchanged. Erasing an account with no events updates zero rows; a None
  account id updates zero rows, never the whole table.
- **Constant statement count.** Seed thousands of events for one account and assert the eraser
  issues one set-based UPDATE regardless of N, completing inside a wall-clock bound — a
  per-row loop inside the product's only irreversible operation is the trap.
- **A concurrent insert cannot break the delete.** Open the eraser transaction, run its
  null-out, then insert an event for that `user_id` from a second session and commit; the
  erase still completes and no event references a missing account.
- **The client erasure is key-scoped.** After deletion the `visitor_id` **and** the frozen UTM
  keys are absent while every other namespaced key — the theme preference at minimum — still
  holds its value. A `localStorage.clear()` implementation satisfies a looser wording and
  destroys the theme.
- **The UTM key must go too, and this is a correctness bug, not tidiness.** First-touch is
  never overwritten, so a surviving frozen set attaches verbatim to the *next* registration
  from that browser. Guard: register A from `/?utm_source=ads&utm_campaign=X`, delete A,
  register B from the same browser with no UTM → B's `utm_*` are all NULL.
- **`oauth_rate_limits` becomes a per-visitor IP log.** The eraser deliberately excludes it on
  the documented reasoning that it "carries no account id in any form" — true when it held
  OAuth-start IPs, false once it keys every anonymous page view. Guard: elapsed-window rows are
  pruned so bucket-row lifetime is bounded and named; the spec states that these rows are
  transient counters rather than retained analytics. **Scope (FOA):** the prune predicate is
  restricted to this story's own bucket key space. OAuth's rows keep the lifetime they have
  today and the sign-in guard keeps the behaviour it has today — Story 14 does not get to
  change how the sign-in abuse bound ages out.

## GeoIP: failure, configuration, disclosure

- **Failure is distinguishable from a legitimate NULL.** Stub the resolver to raise →
  `country IS NULL` **and** a distinct failure signal. Pass a private address → `country IS
  NULL` **and** that signal absent. Without this, a missing database file, an expired key and
  an unforwarded env var all look exactly like localhost — and localhost is the expected result
  in every dev and CI run, so the failure is invisible precisely where it would be caught.
- One stub and assertion per failure mode the dependency can produce — timeout, 4xx, 5xx,
  malformed body — each asserting `country IS NULL` and registration completing normally.
- A hung lookup does not hold the registration request open: the call carries a finite connect
  and read timeout, sized inside the endpoint's budget and inside the client's 25 s deadline,
  with nothing committed after the caller aborted.
- **Config contract (FOA).** With the GeoIP variable unset the application **boots**, country
  resolution is disabled, `country` is NULL, and exactly one structured startup record names
  the disabled resolver — so «unset» is loud in the logs without being fatal to the deploy.
  The `JWT_SECRET` / `GENERATION_PROVIDER` fail-fast pattern is deliberately **not** copied
  here: those variables gate a working product, this one gates a nullable analytics column, and
  a story that must not add a failure reason to registration must not add one to the deployment
  either. What is still enforced: the variable is declared in every compose file the
  infrastructure rule keeps in step and in `backend/.env.example`, since the split backend repo
  must boot standalone, and the disabled-resolver signal is distinguishable from both a
  resolution failure and a legitimate NULL. This keeps the OAuth-variable incident recorded in
  `infra/docker-compose.yml` visible — an unforwarded variable shows up as a named startup
  record rather than as silence.
- Seed the credential with a sentinel, force the resolver to raise, and assert the sentinel is
  absent from captured log output and from the registration response.

## Observability and PII containment

- **The swallow must leave a signal.** Force the emission port to raise on each of the five
  host operations: the operation still succeeds **and** one attributable log record carries
  `event_name` and `visitor_id` as structured fields; the happy path emits no such record. A
  bare `except: pass` satisfies the outcome criterion while analytics fails 100% in production.
- Values from `payload` are carried as structured fields, never interpolated into the message:
  a payload containing `\r\n` produces **one** log record, not two forged lines.
- **The pair is not atomic, and the log must say which half failed.** Fail the second OAuth
  emission: the first stays stored, the callback succeeds, and the record names which event and
  which visitor failed — a half-recorded account is otherwise indistinguishable from a
  returning sign-in.
- **An orphaned start is detectable.** Abort the background task after `complete()` and before
  emission; a signal exists for the `GENERATION_STARTED` that never got its completion. Silence
  must not be the only evidence.
- **Client-side degradation is separable.** Deny storage: the in-memory fallback is entered,
  events still send, and they are marked degraded so Story 15 does not merge an inflated
  visitor count into real behaviour; a rejected send increments a distinguishable drop signal.
- **PII containment, with a sentinel.** Register with a sentinel IP and a sentinel
  `utm_content`; run all eight emissions; assert the sentinel appears in exactly one place —
  the `accounts` row — and is absent from every `analytics_events` row including a text scan of
  `payload`, from every response body, and from captured logs, where the assertion is on a
  fixed redaction token rather than "does not contain the raw string".

## Client behaviour

- **StrictMode double-invoke is real here and documented.** `main.tsx` wraps the app in
  `<StrictMode>`, and `useGeneratedDocumentInit.ts` records in its own words that a `cancelled`
  flag "suppresses the second run's setState but NOT its request, so the POST genuinely fires
  twice". Guards: rendered inside `<StrictMode>` exactly as `main.tsx` does, one page load
  produces exactly one `SITE_VISITED`; one `RegisterForm` mount one `REGISTRATION_STARTED`; one
  `openDocumentId` one `EDITOR_OPENED`, including after an `ErrorBoundary` recovery. Because a
  client cannot unsend an issued request, the collapse is server-side on the occurrence key —
  post the same key twice, assert one row and a success answer both times.
- **The bounce cohort must not be lost.** `httpClient.ts` issues a plain `fetch` with no
  `keepalive`. A visitor who loads and leaves within a few hundred milliseconds — exactly what
  `SITE_VISITED` exists to measure — has the request torn down with the document, and the loss
  is biased rather than random. Guard: emit `SITE_VISITED`, trigger unload immediately, assert
  the request went out via the beacon/keepalive path.
- **Corrupt stored value.** Seed the `visitor_id` key with a non-UUID: the client discards it,
  mints and persists a fresh one, and the event is accepted. "Present → reuse unchanged"
  applied blindly makes that browser's every event 400 forever, silently.
- **Concurrent tabs.** Two contexts over one shared empty store both mint: exactly one
  `visitor_id` persists and both adopt it (write-then-read-back, plus `storage`-event
  adoption). After deletion in one tab, the other stops emitting the erased id.
- **Storage-unavailable fallback is per load.** Two loads produce two different in-memory ids —
  proving no accidental singleton — and the deletion erase step does not throw.
- **Send failure is defined.** Which outcomes count as failed (timeout, 4xx, 5xx, network) is
  named, and each asserts the drop — exactly one attempt, no retry queue, no buffer, so backend
  recovery meets no herd.
- **Ordering across two in-flight sends.** `SITE_VISITED` and `REGISTRATION_STARTED` can be on
  the wire together; dispatch A then B, resolve B first, and the stored rows are still
  orderable A-before-B — carried by `sequence`, which is why the endpoint must assign it on
  arrival order rather than leaving order to `event_time`.

## Scale, pool and load

- Emission adds a second pooled session per product action and a third on the ingest route.
  `session.py` sets no `pool_size`, `max_overflow` or `pool_timeout`, so the defaults are 5+10
  with a 30 s blocking checkout. Pool sizing is stated, and a sustained-rate scenario at target
  concurrency asserts bounded pool-wait and no pool-timeout 500s.
- **Latency, not just outcome.** Make the analytics store hang; registration, login and save
  answer within their normal budget plus the named emission timeout. The outcome criterion
  alone stays green while every user waits 30 seconds.
- `list_stale` has no `LIMIT` and every replica sweeps the same un-jittered tick — the fan-out
  behind the K-versus-M×K guard above. **Not fixed here (2026-08-19):** bounding that query
  changes how the existing sweep behaves, and Story 14 does not need it — the requeue path
  emits nothing, so a recovered row costs this story no extra write. Recorded as a real
  pre-existing scale risk, marked `[S]` out of scope at `03_Load_Tests.md` §3.1 by the
  developer decision of 2026-08-19, and carried as technical debt in
  `ProductSpecification/tasks/7-refactoring-bound-stale-generation-sweep/`.
- `analytics_events` grows at the product's highest row rate with no retention policy. The
  product owner deferred the window deliberately; this story records the deferral and names the
  unbounded store it leaves live, and bounds the one store it can — the rate-limit buckets.

## Handed to Story 15 in writing

So neither story assumes the other owned it:

- `utm_*` and `payload` are stored verbatim by design. **CSV-formula escaping** (`=`, `+`, `-`,
  `@`) and **HTML escaping** are Story 15's, at its sinks. Story 14 guarantees only that what
  was sent is what is stored.
- `visitor_id` is client-asserted and forgeable; no security or revenue decision may key on it.
- `visitor_id` is **nullable**, and a NULL one is a third population: a server-emitted event for
  a generation requested before this migration or by an N-1 replica. Browser-origin rows always
  carry one. Story 15 excludes NULL-visitor rows from visitor-scoped funnels rather than
  treating them as one anonymous visitor.
- An account's `utm_*` are stored **as one set or not at all**. A set may legitimately be
  partial — a link carrying only `utm_source` stores one value and four NULLs — but a set with
  an *unusable* member is stored as five NULLs, never with the bad member dropped and the rest
  kept (FOA / `B2`). So a stored attribution is always exactly what one link carried, and a
  fully-NULL attribution covers both "arrived with no UTM" and "arrived with a link that could
  not be stored". Those two are not distinguishable in the data, by decision.
- Ordering is by `sequence`, never by `event_time` alone.
- Events with `user_id IS NULL` are two different populations — never-registered visitors and
  deleted accounts — and are indistinguishable by design.
- A stored `event_name` the reader does not know is preserved and handled by the stated policy,
  never coerced to the first catalogue constant and never crashing the surrounding read.
- Degraded-mode events (in-memory `visitor_id`) are flagged and must be excluded from unique
  visitor counts.
- The registration funnel has a blind segment between `REGISTRATION_STARTED` and
  `REGISTRATION_COMPLETED`: the catalogue has no name for "did not enter the emailed code", so
  that drop-off is not distinguishable from abandoning the form.
