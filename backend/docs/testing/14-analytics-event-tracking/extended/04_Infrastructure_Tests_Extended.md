<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — Infrastructure Tests (Extended)

Shared test data is inherited from `04_Infrastructure_Tests.md`: the monorepo deployment
definition `infra/docker-compose.yml` with its ports from `infra/.env`, the standalone
`backend/docker-compose.yml` + `backend/Dockerfile`, `backend/.env.example`, the story's
three revisions (`c5d6e7f8a9b0` the `analytics_events` table, `d6e7f8a9b0c1` the ten
registration-context columns on `accounts`, `f8a9b0c1d2e3` the `oauth_state_attribution`
table), the engine's pool values read off the engine itself (SQLAlchemy's `5 + 10` with a
30 s checkout, unchanged by this story), and the `GEOLOCATION_*` / `ANALYTICS_*` settings
with their named defaults.

---

## 1. Migration Against a Populated Database

### TC-14-INFRA-EXT-1.1 — The new columns land on a table that already holds accounts

| Field | Value |
|---|---|
| Description | `d6e7f8a9b0c1` adds ten nullable columns with no default and no backfill to `accounts`. Run against a populated table, a mis-declared column (NOT NULL, or a default) either aborts the upgrade or invents a value for every pre-feature account — which would make the migration itself the largest fabricated cohort in the campaign data. |
| Preconditions | A database at the revision *before* `d6e7f8a9b0c1`, holding ≥ 3 `accounts` rows created with the pre-migration column set (known ids, emails and password hashes recorded). |
| Test data | Revision `d6e7f8a9b0c1`; the ten columns `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, `registration_ip`, `registration_country`, `device_type`, `operating_system`, `device_language`. |
| Steps | 1. Record every pre-existing `accounts` row (id, email, hash, created_at).<br>2. Run `alembic upgrade head`.<br>3. Read the `accounts` column list from the schema catalogue (`information_schema.columns`).<br>4. Re-read every row recorded in step 1 and compare field by field.<br>5. Read the ten new columns on those rows. |
| Expected result | `alembic upgrade head` exits 0 with no error; the catalogue lists all ten columns on `accounts`, each `text` and `is_nullable = YES` with `column_default` NULL; every pre-existing row still reads with byte-identical id, email, hash and created_at, and the row count is unchanged; all ten new values read as SQL NULL on those rows — no `''`, no `UNKNOWN`, no deployment country. |
| Status | Not run |

### TC-14-INFRA-EXT-1.2 — The migration is reversible in the same sense as its predecessors

| Field | Value |
|---|---|
| Description | A downgrade that errors or half-completes leaves a deployment stuck mid-schema; and a downgrade that runs automatically on boot would drop business columns as a side effect of a restart. |
| Preconditions | Database at `head` with `d6e7f8a9b0c1` applied; no process invokes `alembic downgrade` at startup. |
| Test data | `alembic downgrade -1` from `d6e7f8a9b0c1`; the application's startup path (`backend/application/src/app/main.py`) and both compose files' command/entrypoint. |
| Steps | 1. Capture the `accounts` column list at `head`.<br>2. Run `alembic downgrade -1`.<br>3. Capture the `accounts` column list again and the current revision.<br>4. Re-run `alembic upgrade head` and capture the column list a third time.<br>5. Grep the startup path and both compose files' command/entrypoint for any downgrade invocation. |
| Expected result | The downgrade exits 0; all ten columns are absent afterwards and the column list is identical to the pre-migration capture; the recorded revision is `d6e7f8a9b0c1`'s `down_revision`; the re-upgrade restores exactly the same ten columns; no startup path, container command, entrypoint or healthcheck in either compose file invokes `alembic downgrade` — the only route to it is an explicit operator command. |
| Status | Not run |

---

## 2. Rolling Deployment

### TC-14-INFRA-EXT-2.1 — An older instance can still delete an account after the schema has moved

| Field | Value |
|---|---|
| Description | The migration runs before the new code is everywhere, so for a few minutes the deletion path in service is one that knows nothing about `analytics_events`. If that path is left to a plain FK default, the delete either fails on a referencing row or takes the analytics rows with it. |
| Preconditions | Database at `head`; one instance booted from the commit *before* this story, pointed at that database; an account A holding ≥ 3 `analytics_events` rows with `user_id = A`. |
| Test data | Account A `qa.analytics@textery.test` / `Qa!Analytics2026`; the N-1 instance's account-deletion route; A's `analytics_events` row ids recorded before the deletion. |
| Steps | 1. Record A's id and the ids of its `analytics_events` rows.<br>2. Complete the account-deletion flow through the N-1 instance.<br>3. Read the deletion's status code and body.<br>4. `SELECT * FROM accounts WHERE id = A`.<br>5. `SELECT id, user_id FROM analytics_events WHERE id IN (recorded ids)`. |
| Expected result | The deletion answers the N-1 release's own success status (`204`, unchanged) with no error and no `error_code`; no `accounts` row for A remains; all recorded `analytics_events` rows still exist, one for one, with `user_id` NULL — the `ON DELETE SET NULL` on the FK detaches them rather than the delete failing on a referencing row or cascading them away. |
| Status | Not run |

This is the window a rolling deployment actually opens: the migration runs before the new
code is everywhere, so for a few minutes the deletion path in service is one that knows
nothing about the events table.

### TC-14-INFRA-EXT-2.2 — An older instance can still register an account

| Field | Value |
|---|---|
| Description | An N-1 instance sends a register body with no `utm_*` and writes no technical context. If the new columns were declared NOT NULL, or the insert enumerates columns the old code does not set, the whole registration channel fails for the length of the rolling window. |
| Preconditions | Database at `head`; one instance booted from the commit before this story; `qa.rolling@textery.test` not registered. |
| Test data | `POST /api/v1/auth/register` against the N-1 instance with `qa.rolling@textery.test` / `Qa!Rolling2026`, no `utm_*` fields. |
| Steps | 1. `POST /api/v1/auth/register` to the N-1 instance.<br>2. Read the status code and body.<br>3. `SELECT` the created `accounts` row and read all ten new columns.<br>4. Sign in with the same credentials through a *new-release* instance. |
| Expected result | Registration answers the N-1 release's normal success status and body, with no new `error_code`; exactly one `accounts` row is created; all five `utm_*` and all five technical-context columns read as SQL NULL — not `''` and not a placeholder; the sign-in through the new-release instance succeeds, so the row the old code wrote is fully readable by the new one. |
| Status | Not run |

---

## 3. Pool Behaviour

### TC-14-INFRA-EXT-3.1 — A saturated connection pool recovers once load subsides

| Field | Value |
|---|---|
| Description | This story adds a second pooled checkout per product action and a third on the ingest route, against a pool this story deliberately does not re-tune. A checkout leaked on the swallowed-failure branch shows up not as an error but as a pool that never comes back down after the load stops. |
| Preconditions | Backend up against `infra/docker-compose.yml`; the engine's `pool_size`, `max_overflow` and `pool_timeout` read off the configured `AsyncEngine` (today 5 + 10 with a 30 s checkout, per §3.3); `pool.checkedout()` sampled at rest before the run. |
| Test data | Concurrency driven above `pool_size + max_overflow` for 60 s — a mix of `POST /api/v1/analytics/events`, sign-in and document-save — then stopped; `pool.checkedout()` sampled every second through the run and for 60 s after. |
| Steps | 1. Sample `checkedout()` at rest and record it as the resting level.<br>2. Drive load past the pool ceiling for 60 s, sampling `checkedout()` each second.<br>3. Stop the load.<br>4. Keep sampling `checkedout()` for 60 s.<br>5. Issue 20 ordinary requests (one per endpoint touched) and time each one's pool checkout. |
| Expected result | During step 2 `checkedout()` reaches the ceiling read off the engine (`pool_size + max_overflow`) and never exceeds it; within 60 s of the load stopping `checkedout()` is back at the resting level recorded in step 1 — no residue, so nothing was leaked; every step-5 request succeeds with a `2xx` and none waits measurably on the pool (no `TimeoutError`, checkout well under the engine's 30 s `pool_timeout`). |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `accounts created before this feature` | Rows inserted with the pre-migration column set |
| `an instance running the previous release` | The application booted from the commit before this story |
| `connections in use` | SQLAlchemy pool `checkedout()` |
