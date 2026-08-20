<!-- COPIED FILE. Source of truth: ProductSpecification/stories/01-auto-generate-doklad/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: доклад — Load Tests

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`, Load Challenge
Profile). Story 1 is the endpoint this profile is written for — hundreds of concurrent
users submitting generation requests, with request rate, `arq` queue depth, and worker
concurrency as the binding constraint (not per-user data volume or a latency SLO).

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Endpoint under load | `POST /api/v1/generations` |
| Load accounts | `qa.load001@textery.test` … `qa.load200@textery.test`, password `Qa!Load2026` |
| Request body | `{"document_type": "доклад", "topic": "Влияние ИИ на образование", "volume_pages": 3}` with a per-client `Idempotency-Key` |
| Throughput baseline | 200 concurrent clients, sustained **50 requests/second** |
| Load window | 5 minutes of steady state after a 30-second ramp |
| Error-rate ceiling | non-2xx responses ≤ **1 %** of requests over the window |
| Worker concurrency ceiling | the configured in-process concurrency cap (`arq` `max_jobs` once it lands; the `BackgroundTasks` cap today) — record its value before the run, e.g. `10` |
| Provider | stub GigaChat server, instrumented to report concurrent in-flight calls |

Record the baseline numbers actually configured for the run at the top of the result
report; the values above are the ones this suite was written against.

---

## 1. Submission Throughput

### TC-01-LOAD-1.1 — Generation submission sustains the configured throughput baseline

| Field | Value |
|---|---|
| Description | Catches request-handling capacity regressions — most importantly an accidentally-synchronous code path putting the LLM call back inside the request/response cycle, which collapses throughput to the provider's own rate. |
| Preconditions | Backend running with production-like pool sizing; stub GigaChat server responding in a fixed 2 s; 200 load accounts seeded and signed in. |
| Test data | 200 concurrent clients; target **50 req/s**; 5-minute window after a 30 s ramp; error ceiling **1 %** |
| Steps | 1. Ramp 200 clients over 30 seconds.<br>2. Drive `POST /api/v1/generations` at 50 req/s for 5 minutes.<br>3. Record achieved requests/second and the non-2xx count over the window. |
| Expected result | Achieved rate is ≥ 50 req/s sustained for the full 5 minutes (measured, not extrapolated); non-2xx responses are ≤ 1 % of all requests; no request takes longer than the stub's own 2 s provider delay, proving the create path never waits on the provider. |
| Status | Not run |

---

## 2. Queue Depth Under Burst

### TC-01-LOAD-2.1 — A burst of submissions does not exceed the worker concurrency ceiling

| Field | Value |
|---|---|
| Description | Catches a missing or misconfigured concurrency cap, which would let one burst drive unbounded parallel calls to a paid, rate-limited external provider. |
| Preconditions | Backend running with the concurrency ceiling at its configured value; stub GigaChat server counts concurrent in-flight calls and holds each for 5 s. |
| Test data | Burst of **500** submissions in 10 seconds against a ceiling of `10`; provider hold `5 s` per call |
| Steps | 1. Record the configured ceiling value.<br>2. Submit 500 generation requests within 10 seconds.<br>3. Sample the stub's concurrent in-flight call count every 200 ms until the burst drains.<br>4. Read the peak sample. |
| Expected result | The peak concurrent in-flight provider call count never exceeds the configured ceiling (`10` for the values above) at any sample; the remaining ~490 jobs wait and are processed afterwards; every one of the 500 submissions still answers `201` at the API. |
| Status | Not run |

---

## 3. Recovery After a Load Spike

### TC-01-LOAD-3.1 — Throughput recovers after a burst subsides

| Field | Value |
|---|---|
| Description | Catches connection-pool or queue-backlog exhaustion that doesn't self-heal after a spike — promoted from an edge case to critical-path because this story's declared Load Challenge Profile is Throughput, making burst-recovery a first-class concern rather than a nice-to-have. |
| Preconditions | The baseline run of TC-01-LOAD-1.1 has been completed and its error rate recorded. |
| Test data | Baseline **50 req/s**; burst **200 req/s** for 60 seconds; recovery window **60 seconds** after the burst ends; error ceiling **1 %** |
| Steps | 1. Drive the baseline 50 req/s for 2 minutes and record the error rate.<br>2. Ramp to 200 req/s for 60 seconds.<br>3. Drop back to 50 req/s.<br>4. Sample the non-2xx rate every 10 seconds for the following 5 minutes. |
| Expected result | Within 60 seconds of the burst ending the sampled error rate is back at or below the pre-burst baseline (≤ 1 %) and stays there for the rest of the run; the database connection count returns to its pre-burst level; no sustained `500`s or connection-pool timeouts persist past the recovery window. |
| Status | Not run |
