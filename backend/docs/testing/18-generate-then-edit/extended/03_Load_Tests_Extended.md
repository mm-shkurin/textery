<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — Load Tests (Extended)

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

## 1. Retry Behaviour

### TC-18-LOAD-EXT-1.1 — Conversion retries back off under sustained failure

| Field | Value |
|---|---|
| Description | When conversions start failing, an unbounded or fixed-interval client retry loop turns each failed request into a steady stream of new ones, so load rises exactly when the service is least able to serve it — a retry storm that prevents recovery. |
| Preconditions | Backend running from `infra/docker-compose.yml` with ports read from `infra/.env`; the 1500-generation pool seeded; tokens pre-issued; the conversion endpoint injected to fail transiently (`500`) for the whole failure window; the client under test uses the product's real retry policy. |
| Test data | Baseline arrival rate `20 conversions/second`; ramp `10 s`; steady-state window `60 s`; failure injection covering the full 60 s; attempt cap and backoff schedule as configured by the client retry policy (e.g. max 3 attempts, exponential with jitter); error-rate ceiling `< 1 %` non-`2xx` once injection is removed |
| Steps | 1. Ramp to 20 conversions/s over 10 s with failure injection off.<br>2. Turn on `500` injection and hold the offered rate for 60 s, recording total requests received by the server per 5 s bucket.<br>3. Turn injection off and hold 30 s more.<br>4. Compare per-attempt counts and inter-attempt intervals per logical conversion. |
| Expected result | During step 2, server-side arrivals per bucket stay bounded — the last bucket's arrival count is no higher than the first bucket's, with no monotonic increase across the window (no amplification); no logical conversion exceeds the configured attempt cap; successive attempts for one conversion are separated by strictly increasing intervals (backoff, not a fixed retry period); in step 3 the non-`2xx` rate falls back under 1 % within one window, proving the queue was not saturated by retries. |
| Status | Not run |
| Note | Threshold: retry arrivals bounded and backed off; no monotonic amplification. Catches an unbounded client retry loop. |
