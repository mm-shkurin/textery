<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/extended/04_Infrastructure_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — Infrastructure Tests (Extended)

Shared test data is inherited from `04_Infrastructure_Tests.md`: the `infra/docker-compose.yml`
stack with ports read from `infra/.env`, `alembic upgrade head` against a database seeded with
5 000 keyless generations, the `RequeueStaleGenerations` sweep, the pinned `ru-RU-x-icu`
collation, and the bounds `GENERATION_STALE_AFTER_MINUTES=10`, statement deadline `3s`,
search-slot TTL `10s`, retry ceiling `5`, `PAGE_MAX=1000`.

---

## 1. Migration

### TC-12-INFRA-EXT-1.1 — The migration is re-runnable after an interrupted concurrent index build

| Field | Value |
|---|---|
| Description | `CREATE INDEX CONCURRENTLY` that is interrupted leaves an `INVALID` index behind; a migration that does not clean it up either fails forever or ships an index the planner ignores. |
| Preconditions | The seeded database; a `CONCURRENTLY` build of the `(owner_id, idempotency_key)` unique index was killed mid-run, leaving an invalid index. |
| Test data | `SELECT indexrelid::regclass, indisvalid FROM pg_index` for the `generations` unique index. |
| Steps | 1. Confirm an index row exists with `indisvalid = false`.<br>2. Run `alembic upgrade head` again.<br>3. Re-read `pg_index` for that table. |
| Expected result | The command exits `0`; exactly one unique index on `(owner_id, idempotency_key)` exists and it has `indisvalid = true`; no invalid duplicate remains. |
| Status | Not run |

### TC-12-INFRA-EXT-1.2 — The migration aborts rather than blocking when it cannot take its lock

| Field | Value |
|---|---|
| Description | Without `lock_timeout` the migration queues on `ACCESS EXCLUSIVE` and every subsequent query on `generations` queues behind it — one held transaction stalls the whole pipeline. |
| Preconditions | A long-running transaction holds a conflicting lock on `generations`; the sweep is running. |
| Test data | `BEGIN; LOCK TABLE generations IN SHARE ROW EXCLUSIVE MODE;` held open; `lock_timeout` as configured in the migration. |
| Steps | 1. Open the blocking transaction.<br>2. Run `alembic upgrade head` and time it.<br>3. Watch the sweep's ticks during the attempt. |
| Expected result | The migration exits non-zero on its `lock_timeout` within that timeout — it does not wait unbounded; the message names the lock timeout; the sweep keeps requeueing rows throughout and is never blocked behind the migration. |
| Status | Not run |

### TC-12-INFRA-EXT-1.3 — The application starts against a database that has not yet been migrated

| Field | Value |
|---|---|
| Description | In a rolling deploy the new code can reach a database one revision behind; discovering that as an `UndefinedColumn` on a user's first request is an outage instead of a failed rollout. |
| Preconditions | A database at the revision immediately before this story's migration; the new application version deployed against it. |
| Test data | `alembic current` = one revision behind head. |
| Steps | 1. Start the application against that database.<br>2. Read the startup output.<br>3. If it serves, issue `GET /api/v1/projects`. |
| Expected result | The revision mismatch is reported at startup — naming the expected head and the found revision — rather than surfacing later as a query error; no request is answered with a database column error. |
| Status | Not run |

---

## 2. Degraded Database

### TC-12-INFRA-EXT-2.1 — The statement deadline is applied per request, not per connection

| Field | Value |
|---|---|
| Description | A session-level `SET` on a pooled connection is inherited by the next borrower; `SET LOCAL` is what confines the 3 s to the transaction that asked for it. |
| Preconditions | The pool is sized to 1 so the next request provably reuses the same connection. |
| Test data | One projects request that sets the deadline; then a request expected to run ~5 s. |
| Steps | 1. `GET /api/v1/projects?q=климат` and let it complete.<br>2. On the same connection, run `SHOW statement_timeout` outside any transaction.<br>3. Issue the ~5 s operation on that connection. |
| Expected result | Step 2 returns the cluster default, not `3s`; step 3 completes after ~5 s without being cancelled. |
| Status | Not run |

### TC-12-INFRA-EXT-2.2 — A database that answers slowly is bounded, not waited on

| Field | Value |
|---|---|
| Description | The 3 s deadline sits below the gateway read timeout so the client is refused by the app rather than cut off by the gateway while the scan runs on unattended. |
| Preconditions | The database is made to answer more slowly than 3 s (e.g. an injected `pg_sleep` or a throttled volume); account A signed in. |
| Test data | `q=климат`; deadline 3 s; pool checked-out gauge sampled before and after. |
| Steps | 1. Record the checked-out gauge.<br>2. `GET /api/v1/projects?q=климат` and time it.<br>3. Re-read the gauge after the response. |
| Expected result | The request returns within ~3 s with `503` and `{"error_code":"QUERY_TIMEOUT","message":"<generic text>","correlation_id":"<uuid>"}`; the checked-out gauge returns to its step-1 value — the connection is not leaked. |
| Status | Not run |

### TC-12-INFRA-EXT-2.3 — The feed survives a connection dropped mid-request

| Field | Value |
|---|---|
| Description | A connection killed mid-query must be discarded from the pool, not handed to the next request; a pool that recycles a dead connection turns one blip into a run of failures. |
| Preconditions | Account A owns 6 projects; a feed request is in flight when its backend connection is terminated. |
| Test data | `SELECT pg_terminate_backend(<pid>)` for the in-flight query. |
| Steps | 1. Start `GET /api/v1/projects` and terminate its backend connection.<br>2. Read the response.<br>3. Immediately issue the same request again. |
| Expected result | Step 2 fails cleanly with a `5xx` in the `{error_code, message, correlation_id}` envelope — not a hang and not a leaked stack trace; step 3 answers `200 OK` with all 6 projects. |
| Status | Not run |

---

## 3. Configuration Drift

### TC-12-INFRA-EXT-3.1 — Every configured bound is reported at startup

| Field | Value |
|---|---|
| Description | A bound that is documented but not observable cannot be verified on a running deploy; the values in force must be readable without attaching a debugger. |
| Preconditions | The application starts with its configuration complete. |
| Test data | Expected values: `GENERATION_STALE_AFTER_MINUTES=10`, statement deadline `3s`, search-slot TTL `10s`, retry ceiling `5`, `PAGE_MAX=1000`, `limit` max `100`, `q` max `200`, preview `200`. |
| Steps | 1. Start the application.<br>2. Read the startup/readiness output.<br>3. Compare each reported value with the expected list. |
| Expected result | Each of the eight bounds appears with the value actually in force; none is missing and none reports a placeholder or a default that differs from the running behaviour. |
| Status | Not run |

### TC-12-INFRA-EXT-3.2 — A deadline configured above the gateway's is rejected

| Field | Value |
|---|---|
| Description | The whole point of the 3 s deadline is that it fires before the gateway's read timeout; configured above it, the client gets a `504` while the scan runs on and the app never learns it failed. |
| Preconditions | The gateway read timeout is 5 s. |
| Test data | Search statement deadline configured to `8s`; gateway read timeout `5s`. |
| Steps | 1. Set the statement deadline to `8s`.<br>2. Start the application.<br>3. Read the startup output. |
| Expected result | Startup exits non-zero; the message names both values (`8s` deadline and `5s` gateway read timeout); the process never reaches a serving state. |
| Status | Not run |

---

## 4. Search Slots

### TC-12-INFRA-EXT-4.1 — Search slots are released when the holding instance disappears

| Field | Value |
|---|---|
| Description | The slot lives in the database precisely so it survives the process — but that also means a pod killed mid-scan would hold the account's only slot forever without the TTL. |
| Preconditions | Two instances are running; account A's search slot is held by instance 1, which is terminated mid-scan without releasing it. |
| Test data | Slot TTL 10 s; probes at `T+2s` and `T+11s` after the kill. |
| Steps | 1. Start a search on instance 1 and kill that instance mid-scan.<br>2. At `T+2s`, `GET /api/v1/projects?q=климат` via instance 2.<br>3. At `T+11s`, repeat via instance 2. |
| Expected result | Step 2 answers `429` with `{"error_code":"SEARCH_BUSY"}`; step 3 answers `200 OK` — the slot is reclaimed by the TTL alone, with no operator action and no restart. |
| Status | Not run |

---

## DSL Technical Reference

Inherits `04_Infrastructure_Tests.md`.
