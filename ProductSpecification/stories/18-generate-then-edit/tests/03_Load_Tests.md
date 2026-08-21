# Generate → edit — Load Tests

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`). This story adds the
conversion endpoint on top of the generation request rate, and re-invokes story-1's poll
loop. The binding risk is request rate, not per-user data volume.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Generation pool | 1500 completed generations owned by load accounts, each ~4 KB of markdown, seeded before the run |
| Endpoint under load | `POST /api/v1/documents/from-generation` with a fresh `Idempotency-Key` per request |
| Throughput baseline | 20 conversion requests/second sustained (Throughput profile) |
| Window | 60 s of steady state after a 10 s ramp |
| Error-rate ceiling | < 1 % non-`2xx` responses over the window |
| Poll endpoint | `GET /api/v1/generations/{id}` (story-1 owned) |

---

## 1. Conversion Endpoint Throughput

### TC-18-LOAD-1.1 — The conversion endpoint sustains the configured request rate

| Field | Value |
|---|---|
| Description | Catches a parse/sanitize step that does not scale with request rate. Markdown conversion plus sanitization is CPU work on every request, so a per-request cost above the arrival interval shows up as a growing backlog and shed requests. |
| Preconditions | One backend instance against the load database; 1500 completed, unconverted generations seeded; tokens minted once and reused; each request targets a distinct generation so no request short-circuits on the already-converted path. |
| Test data | Constant arrival rate `20 req/s`, ramp `10 s`, steady window `60 s` (1200 requests), one generation per request, a fresh `Idempotency-Key` per request |
| Steps | 1. Ramp to 20 req/s over 10 s.<br>2. Hold 20 req/s for 60 s, recording every status and duration.<br>3. Stop and read the achieved rate, the status histogram and the end-of-window backlog. |
| Expected result | The measured completed rate over the window is >= 20 req/s (>= 1200 responses, no backlog still draining at the end); non-`2xx` responses are < 1 % of the total; every response is `201` (each generation converted once) with no `500`; exactly one document row exists per generation used. |
| Status | Not run |
| Note | `20 req/s` is this suite's stated baseline; if `ProductSpecification/ExpectedLoad.md` later fixes a different figure, update this threshold rather than the runner. |

---

## 2. Poll Load

### TC-18-LOAD-2.1 — Completion polls are spread, not lockstep

| Field | Value |
|---|---|
| Description | Catches a thundering-herd regression on the generation status endpoint: clients started together and polling on a fixed interval arrive together, so the status endpoint sees a spike every interval instead of a flat rate. |
| Preconditions | 200 clients start a generation within a 2 s window; all their generations complete at roughly the same time; the arrival timestamp of every poll request is recorded. |
| Test data | 200 concurrent clients; poll interval `2 s`; required jitter spread — no 200 ms bucket holds more than 25 % of one interval's polls |
| Steps | 1. Start 200 generations within 2 s.<br>2. Let all clients poll until their generations complete.<br>3. Bucket every poll arrival into 200 ms buckets across each interval.<br>4. Compute the peak-to-mean ratio of arrivals per bucket. |
| Expected result | Poll arrivals are spread across each interval — no 200 ms bucket holds more than 25 % of that interval's polls and the peak-to-mean ratio stays below `2.0`; there is no synchronized spike at interval boundaries; the status endpoint's error rate stays under 1 % throughout. |
| Status | Not run |
| Note | Story 1's `useGeneration` owns the poll and its jitter/cap; reconcile the configured interval with that owner rather than pinning a second value here. |
