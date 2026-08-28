> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — Load Tests (Extended)

Same **Throughput** profile as the critical file. These two exercise growth and fan-out
rather than steady rate, which is why they sit here: each catches a real regression, but
neither is on the path that must be green before the story ships.

Shared test data is inherited from `03_Load_Tests.md`: the configured throughput baseline
from `ProductSpecification/ExpectedLoad.md` (concurrency, warm-up and 60 s measurement
window), the `200 req/s` sustained ingest target with its `< 0.5%` non-2xx ceiling, the
test environment's own event rate limit in force (never the production `120 / 60 s`
inherited by omission, per `04_Infrastructure_Tests.md` §3.5), the engine's pool values read
off the engine itself (SQLAlchemy's `5 + 10` with a 30 s checkout, unchanged by this story),
and the emission port with its abandonment allowance.

---

## 1. Growth of the Abuse Counters

### TC-14-LOAD-EXT-1.1 — Counter rows stay bounded as distinct visitors accumulate

| Field | Value |
|---|---|
| Description | The fixed-window counter writes one `oauth_rate_limits` row per `(bucket_key, window_start)`. Nothing prunes elapsed windows today, and until this story nothing filled them — the tokenless ingest route now fills them at one row per distinct address per window, so a table that grows with cumulative traffic is the regression this catches. |
| Preconditions | Backend and Postgres up from `infra/docker-compose.yml` with ports read from `infra/.env`; `oauth_rate_limits` empty at the start of the run; the test environment's own event rate limit in force. |
| Test data | `POST /api/v1/analytics/events` with `event_name: "SITE_VISITED"`, a fresh `visitor_id` and `occurrence_key` UUID per request; ≥ 5000 distinct `X-Forwarded-For` originating addresses driving distinct `client_source()` bucket keys; the clock advanced past `ANALYTICS_EVENT_RATE_WINDOW_SECONDS` (default 60) at least 5 times. |
| Steps | 1. Record `SELECT count(*) FROM oauth_rate_limits` as the resting baseline.<br>2. Drive events from the distinct addresses at the throughput baseline for one window; record the row count and the distinct `window_start` values.<br>3. Advance the clock past the window and repeat step 2 four more times, with a fresh set of distinct addresses each time.<br>4. Read `SELECT count(*), count(DISTINCT window_start) FROM oauth_rate_limits` after the last window.<br>5. Read the non-2xx share and any `TimeoutError` from the SQLAlchemy pool over the whole run. |
| Expected result | The final row count is bounded by `live windows × addresses in those windows`, not by the ≥ 25000 cumulative distinct addresses seen — rows for elapsed `window_start` values are gone, so `count(DISTINCT window_start)` stays at the number of live windows and does not grow to 5; the count after window 5 is not materially above the count after window 1 (no monotonic growth with cumulative addresses); throughput holds `200 req/s` over each window with a non-2xx share `< 0.5%` and zero pool-checkout timeouts. |
| Status | Not run |

`Threshold: stored counter rows must not grow with cumulative distinct addresses.` Catches the
pruning step going missing — the table's own documentation says elapsed-window rows can be
dropped, and until this story nothing dropped them because nothing filled them.

---

## 2. Sweep Fan-Out

### TC-14-LOAD-EXT-2.1 — Recovering stalled generations does not multiply recorded events by instance count

| Field | Value |
|---|---|
| Description | Several replicas run `run_stale_generation_sweep` on the same tick against one database. If the recovery emits per activation rather than per claimed row, the recorded event count becomes M×K — and the sweep that now costs an extra write per recovered row can outlast its own 60 s interval, so activations pile up. |
| Preconditions | One Postgres, `N` application instances each running the sweep loop, all firing within the same tick; `analytics_events` rows counted before the sweep begins. |
| Test data | `K = 500` stalled `generations` rows past `GENERATION_STALE_AFTER_MINUTES` (10); `M = 3` instances; `SWEEP_INTERVAL_SECONDS = 60` from `backend/application/src/app/main.py`; the wall-clock duration of each activation measured from start to return. |
| Steps | 1. Seed 500 stalled generations and record `SELECT count(*) FROM analytics_events`.<br>2. Start the sweep on all 3 instances within the same tick.<br>3. Wait for every activation to return; record each one's wall-clock duration.<br>4. Read `SELECT count(*) FROM analytics_events` and group the new rows by `event_name`.<br>5. Read the claim outcome per generation row (how many activations updated it). |
| Expected result | The number of new `analytics_events` rows attributable to the recovery equals the number of generations recovered — not 3× it — and is independent of the instance count; each of the 500 rows was claimed by exactly one activation (rows-affected 0 for the two losers, whose `ConflictException` is the normal outcome); every activation returns in under 60 s (`SWEEP_INTERVAL_SECONDS`), so no activation overlaps the next; no `TimeoutError` from the SQLAlchemy pool. |
| Status | Not run |

`Threshold: recorded events == stalled generations, independent of instance count; sweep
duration < its interval.` Catches both the M×K emission fan-out and a sweep that outlasts its
own tick once each recovered row costs an extra write.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `many distinct addresses` | Distinct `client_source()` values driving distinct bucket keys |
| `several elapsed windows` | Advance the clock past the fixed window repeatedly |
| `several instances running the recovery sweep` | Multiple `run_stale_generation_sweep` loops against one database |
| `within its window` | Wall-clock duration under `SWEEP_INTERVAL_SECONDS` |
