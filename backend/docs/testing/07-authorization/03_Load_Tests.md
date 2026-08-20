<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Authorization — Load Tests

This story's load tests target the **Throughput** profile declared in
`ProductSpecification/ExpectedLoad.md` (hundreds of concurrent users; capacity-per-second
is the binding constraint). Login/register are otherwise one-shot per-user actions, but
the hazard-scan (group 6) flagged that lockout-counter and verification-code writes share
the DB connection pool with the rest of the backend under concurrent load — that shared
resource is the risk this file exercises, not per-request latency.

Shared test data and thresholds for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Load tool / target | k6 (or Locust) against the prod-copy backend on the port declared in `infra/.env` |
| Throughput baseline | 200 concurrent virtual users, 100 requests/second sustained |
| Baseline window | 5 minutes |
| Error-rate ceiling | < 1% non-2xx/4xx-by-design responses |
| Traffic mix | 40% `POST /auth/login` (half wrong-password), 30% `POST /auth/register` (half duplicate-email), 30% `POST /auth/verify` (half expired-code) |
| Seed accounts | `qa.load.0001@textery.test` … `qa.load.0200@textery.test`, password `Qa!Load2026` |
| Pool metrics | SQLAlchemy pool `checkedout` / `checkedin` sampled every 5 s, pool size and `max_overflow` read from `infra/.env` |

---

## 1. Concurrent Auth Traffic — Connection Pool

### TC-07-LOAD-1.1 — Sustained concurrent login/register traffic stays within the connection pool budget

| Field | Value |
|---|---|
| Description | Catches a connection leak in the lockout-counter or verification-code write paths — the failure branches are the ones most likely to return early without releasing a session. |
| Preconditions | Prod-copy backend and Postgres healthy; the 200 seed accounts exist; pool metrics scraped before the run to establish the idle baseline. |
| Test data | 200 VUs, 100 req/s, 5-minute window, the mixed traffic above including locked-out login, expired-code verify and duplicate-email register |
| Steps | 1. Record the idle `checkedout` count.<br>2. Run the mixed traffic at 100 req/s for 5 minutes.<br>3. Sample pool metrics every 5 s during the run.<br>4. Stop the load and sample again after one 5-second interval. |
| Expected result | Zero pool-acquire timeout responses across the run; peak `checkedout` stays strictly below `pool_size + max_overflow`; within one polling interval of the load ending, `checkedout` returns to the step-1 idle value (typically `0`). |
| Status | Not run |

### TC-07-LOAD-1.2 — Requests beyond pool capacity get a bounded wait or an explicit reject, never an unhandled hang

| Field | Value |
|---|---|
| Description | Undefined exhaustion behaviour surfaces in production as a hung worker or a crashed process rather than a response; the point is that exhaustion has a *defined*, bounded outcome. |
| Preconditions | Backend started with a deliberately small pool (`pool_size=5`, `max_overflow=0`) so exhaustion is reachable; the configured pool-acquire timeout is recorded. |
| Test data | Auth traffic ramped to 3× the pool's capacity (e.g. 300 concurrent requests against 5 connections), 2-minute window |
| Steps | 1. Ramp the mixed auth traffic past pool capacity.<br>2. Record the response status and duration of every request.<br>3. Check that the worker process is still alive and serving after the run. |
| Expected result | Every excess request resolves within the configured pool-acquire timeout — either a normal `2xx`/`4xx` after a bounded wait, or an explicit `500` with the generic `INTERNAL_ERROR` body; zero requests exceed the timeout without a response; no worker restart and no unhandled exception in the log. |
| Status | Not run |

---

## 2. Concurrent Auth Traffic — Sustained Rate

### TC-07-LOAD-2.1 — Login endpoint sustains the configured request rate

| Field | Value |
|---|---|
| Description | Catches a lock-contention hot spot in the atomic failed-attempt-counter update — an `UPDATE … SET count = count + 1` on a hot row serialises and collapses throughput under concurrency. |
| Preconditions | Prod-copy backend healthy; the 200 seed accounts are verified and unlocked. |
| Test data | `POST /api/v1/auth/login` only, 100 req/s for 5 minutes, 50% wrong-password so the counter path is exercised |
| Steps | 1. Run login traffic at 100 req/s for 5 minutes.<br>2. Record achieved requests/second and the error rate.<br>3. Read the failed-attempt counters afterwards. |
| Expected result | Achieved rate is ≥ 100 req/s for the full 5-minute window (no degradation in the final minute); error rate < 1% excluding the by-design `401`/`403` responses; the counters equal the number of wrong-password attempts sent, with no lost increments. |
| Status | Not run |
