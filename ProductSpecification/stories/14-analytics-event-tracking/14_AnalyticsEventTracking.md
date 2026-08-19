# Analytics Event Tracking

## Governing Decision — analytics adapts to the application, never the reverse

Agreed with the developer on 2026-08-19 and binding on every other line in this file, on
`14_AnalyticsEventTracking_AcceptanceCriteria.md`, on `endpoints.md`, on the three API
contracts and on `tests/`. Where anything below appears to conflict with it, this section
wins:

1. **No existing user scenario changes.** Registration, verification, sign-in, OAuth,
   generation, the editor, document saving and account deletion behave after Story 14 exactly
   as they behave before it.
2. **No existing operation gains a new reason to fail** for the sake of analytics or UTM.
3. **No existing HTTP status code or error response changes.** New status codes exist only on
   the one new endpoint, `POST /api/v1/analytics/events`.
4. **Analytics and marketing metadata are fail-open.** If collecting, validating or storing
   them fails, the user operation continues with exactly the result it would have had before
   Story 14 — including its status code, its body and its latency budget.
5. **UTM is metadata, not a gate.** Invalid UTM never blocks registration or OAuth. An
   attribution set that cannot be stored intact is simply not stored (see `FOA` below).
6. **Events record what already happens.** No new user action, screen, button or business rule
   is created so that an event has something to fire on.
7. **Minimum viable analytics.** Nothing is built here for Story 15's convenience that Story 14
   does not itself need.

### FOA — the fail-open attribution rule

- The five `utm_*` are one **set**, frozen first-touch in the browser. `A1 + B2`, agreed
  2026-08-19: if any one member of the set is unusable — over the bound, undecodable, not
  storable text — the **whole set is discarded** and all five columns are stored NULL. The
  account is still created and the sign-in still completes.
- «Unusable» is not «absent». An omitted or empty `utm_*` means *this link carried no such
  parameter*; it is stored NULL and the other four are kept. Only a value that is present and
  cannot be stored triggers the set-wide discard.
- Values are never truncated, and a discard is never surfaced to the user. It is recorded once
  as a structured log record, the same way a failed emission is.
- This holds identically on `POST /auth/register` and on `GET /auth/oauth/{provider}/start`.
  Neither route gains a `400`, a new `error_code`, or any response it does not return today.

## Brief Description

Every product-visible action on the screens that already exist writes one row to a new
`analytics_events` table, keyed by a browser-scoped `visitor_id` and, once signed in, by
`user_id`. Registration additionally stores the account's technical context and its
first-touch marketing attribution.

## Flow

1. First page load mints a `visitor_id` (UUID v4) in `localStorage` when absent, and freezes
   the first non-empty UTM set found in the query string.
2. The client emits `SITE_VISITED` via `POST /api/v1/analytics/events` — no token required,
   carrying a client-minted occurrence key.
3. The registration screen is shown → `REGISTRATION_STARTED` (client).
4. `POST /auth/register` carries the frozen UTM set; the backend derives IP, country, device
   type, OS and device language from the request and stores all eleven values on the account.
   Every one of the eleven is best-effort: anything that cannot be derived or stored is left
   NULL and the registration answers exactly as it does today (FOA).
5. `POST /auth/verify` transitions the account to verified → `REGISTRATION_COMPLETED`, emitted
   by the transition's CAS **winner** only.
6. `POST /auth/login` succeeds → `LOGIN_SUCCESS`. An OAuth callback that creates the account
   emits `REGISTRATION_COMPLETED` **and** `LOGIN_SUCCESS` from one clock reading; a later
   OAuth sign-in emits only `LOGIN_SUCCESS`.
7. `RequestGeneration` persists and enqueues → `GENERATION_STARTED`, and stores the request's
   `visitor_id` on the generation row. `RetryGeneration` emits one more only when it actually
   created a generation. `GenerateDocument` emits `GENERATION_COMPLETED` only when its CAS
   update wins, reading `visitor_id` from the generation row.
8. Opening an existing document in the editor → `EDITOR_OPENED` (client).
9. `SaveDocument` persists content, autosave included → `DOCUMENT_SAVED`, emitted only when a
   row was actually written.
10. Account deletion sets `user_id = NULL` on that account's events and clears the client's
    stored `visitor_id` **and** frozen UTM set.

## Acceptance Criteria

- All 12 catalogue names exist in one domain-owned enumeration; the four subscription names
  are declared, never emitted by this story's code, and **refused** by the public endpoint.
- Each live event is written once per *persisted transition* — never once per HTTP 200.
- An anonymous visitor's event is accepted and stored with `user_id IS NULL`.
- Two page loads from the same browser carry the same `visitor_id`; two tabs opening
  simultaneously on an empty store converge on one; a different browser differs.
- Registration stores all eleven context values; a re-read **in a separate DB session** after
  a **subsequent** save of the same account still returns every one of them.
- First-touch attribution holds across visits, across registration, and across a later
  account created from the same browser after a deletion.
- `country` is `NULL` for loopback, private and unresolvable addresses, and a resolver
  *failure* is distinguishable from that legitimate `NULL`.
- A failure anywhere in the analytics path never changes the outcome **or the latency budget**
  of registration, verification, login, generation or save. This covers the marketing metadata
  too: no `utm_*`, `Accept-Language`, User-Agent or GeoIP value can refuse, delay or alter one
  of those operations.
- Neither `/auth/register` nor `/auth/oauth/{provider}/start` returns any status code or
  `error_code` it did not return before this story. Every request that succeeds today still
  succeeds, with the same body.
- Deleting an account leaves its events with `user_id IS NULL`, touches no other account's
  rows, removes every technical and marketing column with the account row, and leaves every
  other namespaced client key intact.
- No analytics row, payload, response body or log line contains an IP, a UTM value or any
  other personal datum.
- Events for one visitor are totally ordered regardless of which instance wrote them.

The full folded guard set — every hazard-scan finding, written so a test can go red on it —
is in `14_AnalyticsEventTracking_AcceptanceCriteria.md`.

## Validation Rules

| Field | Rule |
|-------|------|
| `event_name` (public route) | accepted set is exactly the three client-origin names (`SITE_VISITED`, `REGISTRATION_STARTED`, `EDITOR_OPENED`); anything else, including the nine server-only and subscription names → 400 `UNKNOWN_EVENT_NAME`, nothing stored |
| `event_name` (column) | CHECK constraint built from the domain tuple of all 12 names, per the `document_type` precedent; a name outside it cannot be stored |
| `visitor_id` | required **on the public route**, native `uuid` column — case and formatting variants collapse to one value; unparseable → 400, never stored raw, never coerced to NULL. The column itself is nullable, for the server-emitted migration-window case only |
| occurrence key | required on client events, native `uuid`; a repeat under the **same** `event_name` for the same visitor stores no second row and still answers success; the same key under a **different** `event_name` → 409, nothing stored; uniqueness is scoped per visitor |
| `user_id` | never read from the body — derived from the Bearer token when present, otherwise NULL; a present-but-invalid token → 401, not silent anonymity |
| `event_time` | assigned from the injected `Clock`, timezone-aware UTC; a client-supplied timestamp is ignored |
| `sequence` | database-assigned monotonic column; the total-order key for one visitor, since `event_time` is equal for the OAuth pair and skews across instances |
| `payload` | optional JSON object; bounded in **bytes**, in nesting depth and in key count; `U+0000` and lone surrogates → 400, never a 500 |
| request body | bounded in **bytes**, enforced on bytes actually read so a chunked body with no `Content-Length` cannot bypass it → 413, canonical envelope |
| `utm_*` (registration and `oauth/start`) | NFC-normalized then bounded in **code points**. Over the bound, undecodable, or carrying text the store cannot hold → the **whole five-value set is discarded** (all five NULL) and the operation continues unchanged; never truncated, never a 400, never a new `error_code` (FOA). Absent or empty → that one value NULL, the rest kept |
| device language | canonical lower-case BCP-47 tag from the highest-q `Accept-Language` entry; unparseable or absent → NULL |
| device type / OS | mapped onto a closed domain taxonomy; an unrecognized User-Agent → NULL, never a catch-all bucket |
| IP | derived server-side via the existing `client_source()`; never accepted from the body; no client → NULL, never the string `"unknown"`. `client_source()` itself is **not modified** — it keys OAuth's sign-in buckets and changing what it returns would change that guard. The `"unknown"` → NULL mapping happens at this story's own storage boundary; moving the helper to a shared REST module is allowed only as a behaviour-preserving move |

## Screen States

**This story adds no screen and no visible element** — a scope decision, not an omission:
reading analytics is Story 15, so `/mockups` is skipped. The client states that must hold:

- First-ever load: `visitor_id` absent → minted, persisted, read back, then used.
- Returning load: a **valid** stored `visitor_id` reused unchanged.
- Stored value present but not a UUID: discarded, a fresh one minted and persisted.
- Two tabs opening at once on an empty store: one `visitor_id` survives and both adopt it.
- Storage unavailable: a per-load in-memory `visitor_id`, events still send, nothing surfaces
  to the user, and those events are marked degraded so Story 15 can separate them.
- Analytics endpoint slow, failing or unreachable: no spinner, no banner, no blocked input.
- After account deletion: `visitor_id` and the frozen UTM set removed by key; every other
  namespaced key untouched; next load mints a new `visitor_id`.

## Core Requirements

- New `analytics_events` table: `id`, `visitor_id` (`uuid`, **nullable**), `user_id` (nullable FK
  to `accounts.id`, **`ON DELETE SET NULL`**), `event_name` (CHECK from the domain tuple),
  `event_time` (timezone-aware), `sequence` (monotonic), `payload` (`NOT NULL`, default `{}`),
  occurrence key. Indexed so Story 15 can page on a total order and so the eraser's predicate
  is not a full scan.
- `visitor_id` is nullable **only** so a server-side emission never has to be dropped or
  faked: the browser route requires it, and a generation that was requested before this
  migration (or by an N-1 replica during the rolling window) still emits its
  `GENERATION_COMPLETED` with `visitor_id` NULL rather than losing the event or inventing a
  sentinel. That third population is handed to Story 15 in writing.
- New nullable columns on `accounts` for IP, country, device type, OS, device language and
  the five `utm_*`; no backfill, and pre-existing rows must still read through
  `find_by_id` and `GET /me`.
- The 12 names live in the domain with no framework import; every emitter reads them there.
- Emission goes through a usecase-layer port implemented by a DB adapter, on **its own
  session acquired in a context manager**, never the request session — the
  `oauth_rate_limits` same-session commit pattern must **not** be copied here.
- Emission runs **after** the caller's transaction commits, is bounded by a named timeout,
  and its failure is swallowed with one structured log record carrying `event_name` and
  `visitor_id` as fields, never interpolated into the message.
- Every server event is emitted by the code path that performed the persisted transition:
  the verify CAS winner, the `GenerateDocument` CAS winner, `RetryGeneration` only when
  `created`, `SaveDocument` only when a row was written. A sweep requeue emits nothing — it
  recovers an occurrence rather than starting one.
- `RequestGeneration` writes the request's `visitor_id` onto the generation row; the
  completion emitter reads it from there, so a sweep-recovered generation on another replica
  still emits with the original visitor's id.
- Country resolution sits behind a usecase-layer port with a finite connect and read timeout
  sized inside the register endpoint's budget; the port distinguishes "resolved to nothing"
  from "resolver unavailable", and its credential never reaches a log.
- The GeoIP configuration is a named env var with a **named default: unset means country
  resolution is disabled**, `country` stays NULL, and one structured record says so once at
  startup. The application boots without it, exactly as it boots today — a story that must not
  add a failure reason to registration must not add one to the deployment either. The variable
  is still declared in every compose file the infrastructure rule keeps in step and in
  `backend/.env.example`, so an operator who wants resolution has one documented place to set
  it. The same holds for every other value this story introduces (the ingest rate limit and its
  window, the emission timeout): named constant, safe default, no new boot failure.
- IP extraction reuses `client_source()`; no second mechanism. The trusted proxy hop depth is
  recorded as a named contract.
- `RegisterUser.execute` grows the registration-context parameters; `AccountModel.from_domain`,
  `to_domain` and `SqlAlchemyAccountRepository.save`'s update branch are updated together. The
  new parameters are optional and add **no branch that can raise**: the usecase's existing
  validation sequence (email format, password policy, confirmation match, duplicate email) is
  untouched, and its set of raised exceptions is unchanged. Unusable context is normalized to
  NULL before it reaches the usecase, never turned into a `ValidationException`.
- `SqlAlchemyAccountEraser` nulls `user_id` with one set-based UPDATE scoped to the account,
  before the account row is deleted, in the same transaction.
- `POST /api/v1/analytics/events` is anonymous-capable and rate-limited with a named limit and
  window, in a bucket key space separate from OAuth's, **failing closed** when the limiter
  itself errors, with elapsed-window rows pruned. Fail-closed and pruning are scoped to this
  new endpoint's own bucket rows: OAuth's existing rows, their lifetime and the sign-in
  guard's behaviour are untouched.
- The client stores `visitor_id` and the frozen UTM set through the existing
  `readStored`/`writeStored` helpers under namespaced keys, removes them by key, and never
  throws when storage is unavailable.
- Client events are dispatched so a page unload does not lose them (`sendBeacon` or
  `keepalive`), are attempted exactly once, and are collapsed server-side by occurrence key
  so React StrictMode's double invoke cannot double-count.
