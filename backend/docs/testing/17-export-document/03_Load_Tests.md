<!-- COPIED FILE. Source of truth: ProductSpecification/stories/17-export-document/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Export document — Load Tests

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`). Export adds CPU-heavy
render work per request; the risk is rate and concurrent render pressure.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Document pool | 50 documents owned by account A, each ~2 pages of HTML, seeded before the run (e.g. `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`) |
| Endpoint under load | `GET /api/v1/documents/{id}/export?format=pdf` |
| Throughput baseline | 20 export requests/second sustained (Throughput profile) |
| Window | 60 s of steady state after a 10 s ramp |
| Error-rate ceiling | < 1 % non-`200` responses over the window |
| Instance under test | one backend instance, worker/render pool as configured in `infra/.env` |

## 1. Export Throughput

### TC-17-LOAD-1.1 — The export endpoint sustains the configured request rate

| Field | Value |
|---|---|
| Description | Catches a render step that does not scale with request rate. The arrival rate is held constant, so a render slower than the arrival interval surfaces as a growing backlog and shed requests rather than as a merely slow run. |
| Preconditions | One backend instance running against the load database; the 50-document pool seeded and owned by the caller; account A's access token minted once and reused. |
| Test data | Constant arrival rate `20 req/s`, ramp `10 s`, steady window `60 s` (1200 requests), `format=pdf`, documents drawn round-robin from the pool |
| Steps | 1. Ramp to 20 req/s over 10 s.<br>2. Hold 20 req/s for 60 s, recording every response status and duration.<br>3. Stop the load and read the achieved rate, the status histogram and the end-of-window backlog. |
| Expected result | The measured completed rate over the 60 s window is >= 20 req/s (>= 1200 responses, with no backlog still draining at the end of the window); non-`200` responses are < 1 % of the total; no `500` from a render-deadline abort appears; the instance is still serving at the end of the run. |
| Status | Not run |
| Note | `20 req/s` is this suite's stated baseline; if `ProductSpecification/ExpectedLoad.md` later fixes a different figure, update this threshold rather than the runner. |

## 2. Concurrent Render Pressure

### TC-17-LOAD-2.1 — Concurrent renders are bounded, not unbounded

| Field | Value |
|---|---|
| Description | Catches a missing render concurrency limit: without a worker pool or backpressure every simultaneous export takes a thread and native heap, so a burst far smaller than the rate capacity can exhaust one instance. |
| Preconditions | One backend instance; the 50-document pool seeded; process RSS, thread count and in-flight render count sampled every 1 s from before the burst until 60 s after it. |
| Test data | Burst of `200` simultaneous `format=pdf` exports issued within 1 s; configured render concurrency cap (worker pool size in `infra/.env`, e.g. `4`); RSS ceiling = baseline + 512 MB |
| Steps | 1. Record baseline RSS, thread count and the configured render cap.<br>2. Fire 200 concurrent export requests.<br>3. Sample concurrent in-flight renders, RSS and thread count throughout the burst.<br>4. After the burst drains, wait 60 s and sample again. |
| Expected result | The observed number of renders executing at once never exceeds the configured cap — excess requests queue or are shed with a defined status instead of all rendering; peak RSS stays below baseline + 512 MB; the process does not restart and no request is left hanging; 60 s after the burst RSS and thread count are back within 10 % of baseline. |
| Status | Not run |
