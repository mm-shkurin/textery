# Analytics Event Tracking — Notes & Considerations

Guards live in `14_AnalyticsEventTracking_AcceptanceCriteria.md`; requirements live in the
spec. This file holds what belongs in neither: pitfalls, dismissals with their reasons, and
the context a reader needs before touching the code.

## Warnings

### Functional Warnings

- **The one defect this story is most likely to ship: a `400` on `/auth/register`.** Every
  instinct while implementing bounds — and every hazard-scan finding that produced them —
  pushes toward refusing bad input at the boundary. On the two existing auth routes that
  instinct is wrong: an over-bound, undecodable or unstorable `utm_*` is **dropped**, the set
  goes with it, and the caller gets the answer they would have got before Story 14 existed.
  The guard scenarios are API §7.5a and §12.10. See the Governing Decision in the spec.
- **The event catalogue is closed, and one funnel step has no name.** The product owner fixed
  12 names. `REGISTRATION_COMPLETED` fires on `/auth/verify`, so the gap between "opened the
  form" and "confirmed the code" is invisible: an abandoned code entry and a bounced form look
  identical in the data. Do not invent a 13th name to close it — raise it with the owner.
- **Four names are declared and dark.** They exist so Stories 8/9 add emitters without a
  migration (the CHECK constraint already lists them). Anyone reading the enum will be tempted
  to wire them to something; there is nothing to wire them to.
- **A sweep requeue emits nothing.** That is a decision, not an oversight: a requeue recovers
  an occurrence rather than starting a new one. The consequence is that a generation which
  stalls and recovers reports one `GENERATION_STARTED` and one `GENERATION_COMPLETED`
  separated by however long the recovery took — which will look like a very slow generation in
  Story 15, and is the honest reading.
- **`user_id IS NULL` means two different things** — a visitor who never registered, and a
  deleted account. By design they are indistinguishable. Any Story 15 metric that says
  "anonymous" is really saying "not currently attributable".
- **First-touch never expires.** A browser that saw a campaign link in March and registers in
  September attributes to March. That is what first-touch means; it is not a bug report.

### UI/UX Warnings

- **This story must remain invisible.** The moment analytics surfaces a spinner, a banner, a
  blocked button or a console error the user can notice, it has failed — every one of the
  three client events fires on a screen the user did not ask to instrument.
- **Do not add a Save button.** Autosave is a valid save; the temptation to create an explicit
  one so `DOCUMENT_SAVED` "means something" was considered and rejected by the product owner.

### Technical Warnings

- **The wiring the spec tells you to reuse is also the wiring that will break you.**
  `oauth_rate_limit_storage` commits the request's session. Copy it into the emitter and the
  emission commits a half-finished business transaction. Reuse the *fixed-window upsert
  shape*, not the session ownership.
- **`verify_account.py` predicted this story.** Its comment names "a future verify side-effect
  (welcome email/token/credit)" and warns that it must re-read rather than trust stale
  in-memory objects. The analytics emitter is that side effect. Read the comment before
  writing the emitter.
- **Three hand-enumerated column lists become fourteen columns.** `from_domain`, `to_domain`
  and `save()`'s update branch. The fakes cannot see an omission — story 13 lost
  `failed_attempt_count` this way. The db test that writes, saves a *second* time, and re-reads
  in a new session is the only thing that catches it.
- **`GenerateDocument` runs where the request no longer exists.** Any design that carries
  `visitor_id` in a closure, a contextvar or task-local state is in-memory application state
  across a multi-instance deployment — forbidden by the coding rules — and simply absent on the
  sweep-recovery path. It goes on the `generations` row. The event's `visitor_id` being
  nullable is **not** a licence to skip that: the NULL exists for generations that predate the
  migration, not for ones this story's own code could have carried the visitor through.
- **React StrictMode fires effects twice in development and the second request really is
  sent.** `useGeneratedDocumentInit.ts` says so in its own comment. Client-side suppression
  cannot fix it; the occurrence key can.
- **CI shares one rate-limit bucket.** Every acceptance test originates from loopback. Without
  a test-environment limit set by contract, the suite becomes one caller and starts throwing
  429s on the most-emitted event in the product — intermittently, which is worse.

## Suggestions & Future Enhancements

- **A `sequence` column is cheap now and impossible later.** It is added here mainly for
  Story 15's paging; if it turns out unnecessary, dropping a column is easier than retrofitting
  a total order onto a populated table.
- **Retention is deferred, not decided.** When the owner sets a window, the natural shape is a
  periodic pruning job — which is a destructive periodic operation and will need its own hazard
  scan, not a `DELETE` bolted onto the sweep.
- **The blind funnel segment** (above) could be closed later by a `REGISTRATION_CODE_ENTERED`
  name if the owner ever wants email-confirmation drop-off measured.
- **`oauth_rate_limits` is now misnamed.** Once analytics keys into it, the table serves two
  subsystems. Renaming it is a migration nobody needs this week; noting it so the next person
  is not confused by an OAuth-named table full of page-view buckets.

## Technical Notes

### Load Considerations

`ExpectedLoad.md` puts this project on a **Throughput** profile: hundreds of concurrent users,
request rate binding, no p95/p99 SLO and no batch pipeline. Story 14 is the story that makes
that profile bite, for two reasons that compound:

1. It writes one row per action of **every** visitor, anonymous included — a higher row rate
   than any existing path.
2. It adds a second pooled session per action and a third on the ingest route, while
   `session.py` leaves `pool_size` / `max_overflow` / `pool_timeout` at SQLAlchemy's defaults
   (5 + 10, 30 s blocking checkout) — **and this story leaves them there.** Changing the pool
   changes how every existing endpoint behaves under load, which is not a change an analytics
   story makes on a prediction. The load scenarios measure against the real pool; if they show
   the second checkout exhausting it, that is a measurement to bring to the developer, not a
   tuning to slip in.

The load scenario is therefore in scope — unusually for this project, where several stories
skipped it correctly. Assert sustained request rate, bounded pool-wait and no pool-timeout
500s; do not assert latency percentiles or full-table volume scale.

### Security Considerations

- The product's **first public unauthenticated write endpoint**. Everything else behind
  `/api/v1` requires a Bearer token. Treat the accepted-set narrowing, the fail-closed limiter
  and the no-echo error bodies as the security surface, not as validation polish.
- `client_source()` changes status: it was a best-effort abuse bound whose own docstring says
  no security invariant rests on it, and this story makes its output **durable business data**
  on the account row. The value differs by environment by construction — socket peer locally,
  rightmost `X-Forwarded-For` hop behind nginx, and something else again the day a CDN appears.
- The first durable PII beyond the email address. There is no privacy policy and no retention
  policy anywhere in the project; the owner deferred both. What this story can control — that
  PII lands in exactly one place and never in events, payloads, responses or logs — is guarded.

### Infrastructure Notes

- The GeoIP dependency needs an env var and a line in **all three** compose files per
  `.claude/rules/infrastructure.md` — the monorepo's `infra/`, and the standalone `backend/`
  one, which must boot cloned on its own. It does **not** get a fail-fast boot contract:
  absent means resolution is disabled, `country` stays NULL, and one startup record says so.
  A deployment that upgrades without the variable must still start.
- Whatever GeoIP adapter is chosen carries a licence and a file weight. The font decision
  (known-debt #15) is the precedent: licence and shippability are part of the choice, not a
  detail settled after it.
- Rolling deploy matters here: `backend/Dockerfile` runs `alembic upgrade head` before
  `uvicorn`, so the new schema is live while N-1 replicas serve. That is why the FK carries
  `ON DELETE SET NULL` rather than relying on an eraser step the old replicas do not have.

### Integration Notes

- One new outbound dependency (GeoIP), on the registration path, with a finite timeout sized
  inside the endpoint's budget and inside the frontend's 25 s `REQUEST_TIMEOUT_MS` — which
  deliberately does not auto-retry, because "giving up on a response never unsends the request".
- No queue, no broker, no outbox. Delivery is at-most-once with a swallowed failure, by product
  decision: a lost event must never fail a user operation. The catalogue's usual eventual-
  delivery guard is therefore **declined deliberately**, and the compensating requirement is
  that the loss is visible in logs rather than silent.

## Hazard classes dismissed, with reasons

Recorded because a dismissal and a class that was never checked look identical otherwise.

- **Money & mixed units (g1)** — no currency, percentage or scaled quantity in this story. Only
  the "same quantity, two units" half fired, on the size bounds.
- **Pagination & cursor stability (g6)** — Story 14 ships no read endpoint. The obligation that
  survives is schema-side: a total order for the reader Story 15 will build.
- **Sort/filter allow-list, read-side IDOR (g5)** — same reason: no read surface here.
- **Optimistic render (g8)** — the story adds no visible element, so nothing renders ahead of
  the server.
- **Unsaved-input loss (g8)** — no new form field. The register form's existing
  `useUnsavedGuard` is untouched.
- **Dead-letter / poison message (g3)** — no queue and no retry exist to dead-letter into.
- **Local-day bucketing (g7)** — Story 14 writes UTC instants only; date-bucket correctness is
  Story 15's reporting concern.
- **Periodic-job overlap (g3)** — this story adds no periodic job; the existing sweep is
  already made mutually exclusive by the storage CAS.
- **Migration `downgrade()` (g4)** — it drops populated columns, but identically in kind to all
  22 existing migrations, and only ever by explicit operator command.

## Additional Context

`interview.md` carries the product-owner decisions this spec implements, including the three
resolved at interview time (the `/verify` emission point, the OAuth double event, and the fate
of events at account deletion) and the reasoning for `visitor_id` living in `localStorage`
while auth tokens deliberately live in `sessionStorage`.

Two things the interview left to design that the hazard scan then decided, so the spec and the
interview do not read as contradicting each other:

- The interview deferred **how** `visitor_id` reaches the completion emitter to
  `/design-preview`. The scan closed it: a column on `generations`, because the recovery path
  has no request to carry it and the coding rules forbid in-memory state.
- The interview described the public endpoint as accepting the contract's names. The scan
  narrowed the **enforced** set to the three a client legitimately emits, which is strictly
  stronger and removes the forged-`SUBSCRIPTION_ACTIVATED` hole.
