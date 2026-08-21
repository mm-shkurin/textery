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
> 1.1 refuses almost all of its own traffic and goes red for rate limiting, which is not the
> regression it exists to catch. The override is a contract, named in the DSL table below, not
> an incidental test setting.

---

## 1. The Ingest Endpoint

### 1.1 The events endpoint sustains the anonymous visitor rate
```gherkin
Given the configured throughput baseline
And the test environment's own event rate limit in force
And every request arriving without a session
When site visits are reported at the target rate for the measurement window
Then the endpoint sustains that rate
And the error rate stays under the ceiling
And no request fails for want of a database connection
```

`Threshold: 200 req/s sustained over 60s, error rate < 0.5%, zero pool-checkout timeouts.`
Catches the regression this story most plausibly ships: a per-request session leak on the
swallowed-failure branch, or an unbounded pool wait once every visitor action opens a second
checkout.

---

## 2. Emission Riding On Product Endpoints

### 2.1 Product endpoints hold their rate with emission switched on
```gherkin
Given the configured throughput baseline
When accounts sign in and save documents at the target rate for the measurement window
Then both endpoints sustain the rate they sustain without emission
And the error rate stays under the ceiling
```

`Threshold: the sign-in and save rates must not regress by more than 10% against the same
run with the emission port disabled.` Catches the doubling of pooled checkouts per action —
the failure that only appears at concurrency, never in a single-request test.

### 2.2 A recorder that never answers does not slow the operations it observes
```gherkin
Given the configured throughput baseline
And the event recorder does not answer
When accounts register and save documents at the target rate
Then each operation still answers within its normal budget plus the recorder's abandonment allowance
And no operation waits on a database connection for longer than the pool's stated ceiling
```

`Ceiling: normal endpoint budget + the named emission timeout.` Catches the shape the
acceptance criteria alone cannot see: a swallowed failure that still costs the user the full
default 30-second pool checkout before it is swallowed.

---

## 3. The Recovery Sweep

>  **[S] OUT OF SCOPE FOR STORY 14 — decided 2026-08-19.** §3.1 is **not implemented in this
> story**. It requires a `LIMIT` on `GenerationStorage.list_stale`, which has none today, and
> that changes how the existing recovery sweep behaves for every generation. The governing
> principle stands: *analytics adapts to the existing application; the existing application is
> not changed for analytics.* The unbounded query is a genuine pre-existing scale risk — it
> predates this story, and Story 14 does not need it fixed, because the requeue path emits
> **nothing** by design, so a recovered row costs this story no extra write (the completion
> write it does cost is the one an ordinary generation already costs). Carried as technical
> debt in `ProductSpecification/tasks/7-refactoring-bound-stale-generation-sweep/`. §1 and §2
> are unaffected and are in scope.

### 3.1 [S] The recovery sweep reads a bounded batch, never the whole backlog — *out of scope for Story 14, see task 7*
```gherkin
Given the configured throughput baseline
And a backlog of stalled generations far larger than the sweep's batch size
When one sweep activation runs
Then it fetches at most its batch size in one query
And the remaining backlog is drained across subsequent activations
And no activation loads the whole backlog into memory
```

`Threshold: rows fetched per activation <= the named batch size, independent of backlog
depth.` The stale-generation query carries no limit today, and this story makes every
recovered row cost an additional write — a backlog after an outage is exactly when the set is
largest and when the extra write hurts most.

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
| `the recorder's abandonment allowance` | The named emission timeout from `14_AnalyticsEventTracking.md` |
| `the pool's stated ceiling` | The configured engine's own `pool_timeout`, read off the engine per `04_Infrastructure_Tests.md` §3.3 — today's effective value, which this story does not change |
| `the sweep's batch size` | The named limit on the stale-generation query — *no such limit exists today; the row belongs to the skipped §3.1* |
