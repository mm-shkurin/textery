<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Analytics Event Tracking — Load Tests

Profile: **Throughput** (`ProductSpecification/ExpectedLoad.md`) — hundreds of concurrent
users, request rate is the binding constraint. This story is the one that makes that profile
bite: it writes a row per action of *every* visitor including anonymous ones, and it adds a
second pooled session per product action and a third on the ingest route, while `session.py`
leaves `pool_size` / `max_overflow` / `pool_timeout` at their defaults — **and this story
leaves them there** (`04_Infrastructure_Tests.md` §3.3). Which is precisely why these scenarios
are the ones that decide whether that has to change: they measure the doubled checkout against
the pool the application actually runs with, rather than against one this story quietly
re-tuned to make its own numbers work.

Out of scope for this profile: single-request latency percentiles and full-table volume
seeding. The one timing assertion below is a **budget ceiling**, not an SLO — it exists
because "analytics never changes the outcome" says nothing about how long the user waits.

> **Every scenario here runs under the test environment's own rate limit.** The production
> limit is 120 requests per 60 s per bucket keyed on `client_source()`, and every load
> generator originates from loopback — one bucket. Run against the production value, scenario
> TC-14-LOAD-1.1 refuses almost all of its own traffic and goes red for rate limiting, which is
> not the regression it exists to catch. The override is a contract, named in the DSL table
> below, not an incidental test setting.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Ingest endpoint | `POST /api/v1/analytics/events`, tokenless, answers `204 No Content` |
| Event body | `{"event_name":"SITE_VISITED","visitor_id":"<v4 UUID>","occurrence_key":"<v4 UUID>","payload":{}}` — one fresh `occurrence_key` per virtual request, so nothing collapses |
| Seeded accounts | 200 accounts `qa.load001@textery.test` … `qa.load200@textery.test` / `Qa!Load2026`, each with a Bearer token and at least one document |
| Product endpoints under load | `POST /api/v1/auth/login` (`200`), document save (`200`), `POST /api/v1/auth/register` (`201`) |
| Target rate / window | 200 req/s sustained over 60 s, after a 30 s warm-up that is not measured |
| Error-rate ceiling | non-2xx share < 0.5 % of responses over the window |
| Production rate limit (**not** in force here) | `ANALYTICS_EVENT_RATE_LIMIT=120` per `ANALYTICS_EVENT_RATE_WINDOW_SECONDS=60`, bucketed on `client_source()` |
| Test-environment rate limit | `ANALYTICS_EVENT_RATE_LIMIT=<TEST_RATE_LIMIT>` — **PLACEHOLDER**: the acceptance environment sets it explicitly (`04_Infrastructure_Tests.md` §3.5), but no document states the number |
| Pool bounds in force | `session.py` sets neither `pool_size`, `max_overflow` nor `pool_timeout` — SQLAlchemy defaults (`pool_size=5`, `max_overflow=10`, `pool_timeout=30 s`), read off the running engine, never hardcoded in the scenario |
| Emission abandonment allowance | `RECORDING_TIMEOUT_SECONDS = 2.0` (`server_event_recorder.py`) |
| Measured signals | throughput counter, non-2xx share, pooled checked-out gauge, pool `TimeoutError` count, per-request duration |

---

## 1. The Ingest Endpoint

### TC-14-LOAD-1.1 — The events endpoint sustains the anonymous visitor rate

| Field | Value |
|---|---|
| Description | Catches the regression this story most plausibly ships: a per-request session leak on the swallowed-failure branch, or an unbounded pool wait once every visitor action opens a second checkout. The route is tokenless, so its traffic is bounded only by how many people load the site. |
| Preconditions | Backend running at its configured replica count; the test environment's own event rate limit in force, not the production 120 per 60 s; pooled checked-out gauge recorded at baseline; `analytics_events` at its seeded size. |
| Test data | `POST /api/v1/analytics/events` with no `Authorization` header; `event_name=SITE_VISITED`; a fresh `visitor_id` and `occurrence_key` per request; 200 req/s for 60 s after a 30 s warm-up. |
| Steps | 1. Read `pool_size`, `max_overflow` and `pool_timeout` off the running engine and record the checked-out baseline.<br>2. Ramp anonymous `POST /api/v1/analytics/events` to 200 req/s over the 30 s warm-up.<br>3. Hold 200 req/s for the 60 s measurement window.<br>4. Sample the throughput counter, the non-2xx share and the checked-out gauge across the window.<br>5. Count pool `TimeoutError`s raised during the run and re-read the gauge 30 s after the last request. |
| Expected result | Measured throughput is ≥ 200 req/s across the whole 60 s window with no dip below it; every accepted request answers `204`; non-2xx share < 0.5 % and zero `429 RATE_LIMITED` (the test limit is in force); zero pool checkout `TimeoutError`; the checked-out gauge never reaches `pool_size + max_overflow` and returns to its recorded baseline within 30 s of the last request. |
| Status | Not run |

---

## 2. Emission Riding On Product Endpoints

### TC-14-LOAD-2.1 — Product endpoints hold their rate with emission switched on

| Field | Value |
|---|---|
| Description | Catches the doubling of pooled checkouts per action — the failure that only appears at concurrency and never in a single-request test. Each sign-in and each save now opens a second session of its own for the event, against a pool this story deliberately does not resize. |
| Preconditions | The 200 seeded accounts exist with their documents; the same build can be run twice — once with the emission port wired, once with it swapped for `NullAnalyticsRecorder`. |
| Test data | Mixed load of `POST /api/v1/auth/login` and document save at 200 req/s total for 60 s; identical script, seed and account set for both runs. |
| Steps | 1. Run the baseline with the emission port swapped for the no-op recorder: 200 req/s for 60 s; record per-endpoint throughput and non-2xx share.<br>2. Restore the real emission adapter and repeat the identical run.<br>3. Compare per-endpoint throughput between the two runs.<br>4. Sample the checked-out gauge and count pool `TimeoutError`s during the emission run. |
| Expected result | With emission on, the sign-in rate and the save rate are each within 10 % of the same endpoint's baseline rate — no more than a 10 % regression; both runs sustain ≥ 200 req/s in total over the window; non-2xx share < 0.5 % in the emission run; zero pool checkout `TimeoutError`; every request that succeeded in the baseline succeeds here with the same status, and no request answers non-2xx because of an event. |
| Status | Not run |

### TC-14-LOAD-2.2 — A recorder that never answers does not slow the operations it observes

| Field | Value |
|---|---|
| Description | Catches the shape the acceptance criteria alone cannot see: a swallowed failure that still costs the user the full default 30-second pool checkout before it is swallowed. "The failure never changes the outcome" is satisfied by a request that answers `201` thirty seconds late. |
| Preconditions | Emission port stubbed to accept the call and never answer, hanging past `RECORDING_TIMEOUT_SECONDS = 2.0`; a healthy-recorder baseline for the same endpoints recorded first; pool bounds read off the running engine. |
| Test data | `POST /api/v1/auth/register` (`201`) and document save (`200`) at 200 req/s for 60 s; hanging recorder stub; ceiling per endpoint = its healthy-recorder duration + 2.0 s. |
| Steps | 1. Record each endpoint's duration distribution against a healthy recorder.<br>2. Install the hanging recorder stub.<br>3. Run register and save at 200 req/s for 60 s.<br>4. Measure each endpoint's maximum request duration and the non-2xx share.<br>5. Measure the longest single wait for a pooled connection, count pool `TimeoutError`s, and re-read the checked-out gauge after the run. |
| Expected result | No register or save request exceeds its step-1 duration plus 2.0 s; non-2xx share stays < 0.5 %, every register still answers `201` and every save `200`; no request waits for a pooled connection longer than the engine's own `pool_timeout` (30 s at today's defaults) and zero pool `TimeoutError`s are raised; the checked-out gauge returns to baseline within 30 s of the last request, proving the abandoned emissions released their own sessions. |
| Status | Not run |

---

## 3. The Recovery Sweep

>  **[S] OUT OF SCOPE FOR STORY 14 — decided 2026-08-19.** TC-14-LOAD-3.1 is **not implemented
> in this story**. It requires a `LIMIT` on `GenerationStorage.list_stale`, which has none today,
> and that changes how the existing recovery sweep behaves for every generation. The governing
> principle stands: *analytics adapts to the existing application; the existing application is
> not changed for analytics.* The unbounded query is a genuine pre-existing scale risk — it
> predates this story, and Story 14 does not need it fixed, because the requeue path emits
> **nothing** by design, so a recovered row costs this story no extra write (the completion
> write it does cost is the one an ordinary generation already costs). Carried as technical
> debt in `ProductSpecification/tasks/7-refactoring-bound-stale-generation-sweep/`. Sections 1
> and 2 are unaffected and are in scope.

### TC-14-LOAD-3.1 — [S] The recovery sweep reads a bounded batch, never the whole backlog — *out of scope for Story 14, see task 7*

| Field | Value |
|---|---|
| Description | The stale-generation query carries no limit today, and this story makes every recovered row cost an additional write — a backlog after an outage is exactly when the set is largest and when the extra write hurts most. Skipped for this story: the batch size the case asserts against does not exist yet. |
| Preconditions | A backlog of stalled generations far larger than the sweep's batch size — 10 000 rows past `GENERATION_STALE_AFTER_MINUTES=10`; a named `LIMIT` on `GenerationStorage.list_stale` (**PLACEHOLDER — no such limit exists today; task 7 introduces it and names its value**). |
| Test data | 10 000 stale generations, then 50 000; batch size `<SWEEP_BATCH_SIZE>` — **PLACEHOLDER, undefined until task 7**; three consecutive sweep activations; the emitted SQL captured. |
| Steps | 1. Seed 10 000 stale generations.<br>2. Run one `RequeueStaleGenerations` activation and capture the SQL it issued.<br>3. Count the rows the selecting statement returned and the process's peak resident set during the activation.<br>4. Run two further activations, counting the rows each fetched and the remaining backlog after each.<br>5. Repeat steps 2–4 against a 50 000-row backlog. |
| Expected result | Each activation's stale query carries a `LIMIT` equal to the named batch size and returns at most that many rows; the rows fetched per activation are identical for the 10 000-row and the 50 000-row backlog — independent of backlog depth; the backlog decreases by at most the batch size per activation and is drained across successive activations; peak resident set during an activation does not grow with backlog depth; zero `analytics_events` rows are written by any requeue. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's load baseline per `ExpectedLoad.md` — concurrency, warm-up and measurement window |
| `the test environment's own event rate limit in force` | The rate limit set by contract for the acceptance/load environment, asserted by `04_Infrastructure_Tests.md` §3.5 — never the production default inherited by omission |
| `sustains that rate` | Throughput counter over the window, not a per-request timer |
| `the error rate ceiling` | Non-2xx share of responses over the window |
| `no request fails for want of a database connection` | Zero `TimeoutError` from the SQLAlchemy pool; checked-out connections return to baseline after the run |
| `the same run with the emission port disabled` | Baseline run with the emission adapter swapped for a no-op |
| `the recorder does not answer` | Emission port stubbed to hang past its timeout |
| `the recorder's abandonment allowance` | The named emission timeout from `14_AnalyticsEventTracking.md` — `RECORDING_TIMEOUT_SECONDS = 2.0` |
| `the pool's stated ceiling` | The configured engine's own `pool_timeout`, read off the engine per `04_Infrastructure_Tests.md` §3.3 — today's effective value, which this story does not change |
| `the sweep's batch size` | The named limit on the stale-generation query — *no such limit exists today; the row belongs to the skipped TC-14-LOAD-3.1* |
