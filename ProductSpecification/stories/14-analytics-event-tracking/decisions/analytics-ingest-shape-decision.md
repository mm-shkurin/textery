# Decision: The shape of the analytics ingest path

**Date**: 2026-08-20 **Scenarios**: 1.1 (fixes the shape), consumed by 1.2, 1.3, 2.x, 3.x, 5.x, 6.x, 11.x

The `/design-preview` hazard scan for 1.1 ran all eight catalogue groups and returned 46
GAPs, of which the large majority were one finding restated: the drafted shape had **no
home** for behaviour `endpoints.md` and `analytics_events_create.yaml` already mandate.
Five of the choices below are non-obvious enough that a later scenario would otherwise
re-argue them, and two of them look correct until they are traced.

| Rejected | Why |
|----------|-----|
| `UNIQUE (visitor_id, occurrence_key)`, plain | Postgres defaults to `NULLS DISTINCT`, so a row with either column NULL conflicts with nothing. Server-emitted rows carry `occurrence_key IS NULL` and `visitor_id` is nullable for the rolling-deploy window — the story's only store-level dedupe would be silently void on exactly the rows the nullability was introduced for. Found independently by groups 02 and 03. |
| `UNIQUE ... NULLS NOT DISTINCT` (available on PG16) | Group 03's proposed fix, and wrong in the other direction: with `occurrence_key IS NULL` on every server-emitted row, all NULLs become equal and **every server event for one visitor collapses into a single row**. It converts a missing guard into silent data loss. |
| Read-then-insert to decide 204 vs 409 | Passes the sequential-replay scenario and writes two rows under the same-instant case — the exact hazard §5.5 names ("the collapse is enforced by the store itself, not by a prior read"). React StrictMode makes the concurrent case ordinary, not rare. |
| `degraded` stored as a `payload` key | `payload` carries a no-PII rule and a 64-key cap, and is stored verbatim for Story 15. A marker that governs whether a row counts toward unique visitors cannot live inside the free-form blob it is meant to qualify. |
| `sequence` described as the "total-order key" | An IDENTITY value is assigned at INSERT and becomes visible at COMMIT, and the two orders differ under concurrency. Story 15 reads this design as its warrant and would build a tailing cursor on it, permanently skipping rows whose transaction committed late. |
| Deferring the unique constraint and `sequence` to their own scenarios (the TDD-minimal migration) | Both become migrations on a hot table. Adding the unique constraint after the route has served StrictMode double-fires aborts on the existing duplicates; adding `sequence BIGINT IDENTITY` to a populated table is a full rewrite holding `ACCESS EXCLUSIVE` on the product's busiest write path. |

**Chosen**: one migration creating the whole table; the port, the column set, the
validation step and the collaborator slots land at 1.1 as **shape**, each guard landing
with the scenario that asserts it.

## Model

- `AnalyticsEventRepository.save_new(event) -> SaveOutcome` — `STORED` /
  `ALREADY_RECORDED` / `CONFLICTING_NAME`. A `-> None` port cannot express the contract's
  204-vs-409 branch, and the same port is later handed to the server-emitted path.
- The adapter decides the collapse with `INSERT ... ON CONFLICT (visitor_id,
  occurrence_key) DO NOTHING RETURNING id`, never a prior read.
- Partial unique index on `(visitor_id, occurrence_key) WHERE occurrence_key IS NOT NULL`
  — the constraint governs client-origin rows only. Dedupe for server-emitted events is a
  separate mechanism, named by the scenario that introduces it, not inherited from here.
- `analytics_events.degraded` — `BOOLEAN NOT NULL DEFAULT false`.
- `analytics_events.sequence` — `BIGINT GENERATED ALWAYS AS IDENTITY`. Contract: a stable
  unique **sort** key. Explicitly **not** gap-safe as a tailing cursor.
- `analytics_events.user_id` — FK to `accounts.id`, `ondelete="SET NULL"` stated
  explicitly. The repo's prevailing convention for `accounts` children is `NO ACTION` plus
  an ordered delete in `SqlAlchemyAccountEraser`; this table deliberately departs from it,
  so the eraser's hand-maintained docstring gains `analytics_events` and its action.
- Analytics rows **survive** account erasure with `user_id` nulled. This is a retention
  decision, not an oversight: Story 15's cohort figures need the rows. It makes
  `DeleteAccount`'s "removes an account and everything that belongs to it" partially
  false, which is why it is recorded here rather than in a table cell.
- `RecordAnalyticsEvent` gains a payload-validation step and constructor slots for the
  rate limiter and the failure-log emitter. The slots are unwired at 1.1; the bounds,
  the 429/503 behaviour and the log record land at 3.x, 6.x and Infra 1.1.
- Every request DTO field is typed permissively **and defaulted**, `payload` and
  `degraded` included. A strict annotation or a missing default returns Pydantic's 422,
  which echoes the rejected input back on the product's only tokenless route.
- Value objects guard `isinstance(raw, str)` before parsing, as `IdempotencyKey` already
  does: `uuid.UUID` raises `AttributeError`/`TypeError` on a non-string, not `ValueError`.

## Edge Cases

| Case | Behavior |
|------|----------|
| `Authorization` header absent | Anonymous — `user_id` stored NULL |
| `Authorization:` sent with an empty value, or `Bearer ` with no token | 401, nothing stored. Never downgraded to anonymous — `Header(default=None)` yields `""`, not `None`, so the obvious `if not authorization: return None` would silently admit both as anonymous |
| The account-existence lookup errors or hangs while a token is present | Refused, nothing stored. Not stored as anonymous — a fail-open wrapper here admits a forged token as an anonymous event |
| `payload` omitted, explicit `null`, or `{}` | All three store `{}` |
| `payload` present but not an object (`[]`, `0`, `""`, `false`) | Refused as `INVALID_PAYLOAD`. A bare `payload or {}` would store all four as "no context" — a fourth state the contract never granted |
| The commit fails after the row was written | Non-204, and a fresh read finds nothing. A 204 must never be answered for a row that did not persist |
| A name is added to the domain `EVENT_NAMES` tuple without a migration | Infra §1.6 goes red in CI, because it iterates `EVENT_NAMES` rather than a literal twelve and CI runs `alembic upgrade head` against the test database. Written as twelve literals it would stay green through the drift forever |
| The new route lands | `backend/application/tests/test_every_route_states_whether_it_needs_a_token.py` goes red until `("POST", "/api/v1/analytics/events")` is added to `_DELIBERATELY_PUBLIC` with its reason — the deliberate reviewable line that file exists to force |
