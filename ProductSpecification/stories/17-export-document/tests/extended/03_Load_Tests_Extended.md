> These are additional edge case tests. Implement after core tests pass.

# Export document — Load Tests (Extended)

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`). Export adds CPU-heavy
render work per request; the risk is rate and concurrent render pressure.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Document pool | 50 documents owned by account A, each ~2 pages of HTML, seeded before the run (e.g. `7f1c2d84-0b2e-4c31-9a55-2f7b41d0e913`) |
| Endpoint under load | `GET /api/v1/documents/{id}/export?format=pdf|docx` |
| Throughput baseline | 20 export requests/second sustained (Throughput profile) |
| Window | 60 s of steady state after a 10 s ramp |
| Error-rate ceiling | < 1 % non-`200` responses over the window |
| Instance under test | one backend instance, worker/render pool as configured in `infra/.env` |

## 1. Mixed Format Load

### TC-17-LOAD-EXT-1.1 — Sustained mixed PDF and DOCX exports hold the rate

| Field | Value |
|---|---|
| Description | The two formats go through different render backends. A single-format run can pass while the other backend is the bottleneck; only a mixed run exposes a format-specific render bottleneck. |
| Preconditions | Backend running from `infra/docker-compose.yml` with ports read from `infra/.env`; the 50-document pool seeded; account A's token pre-issued so login is not in the measured path; a warm-up run discarded. |
| Test data | Arrival rate `20 requests/second` sustained, split `50 % format=pdf` / `50 % format=docx`, document id drawn at random from the pool; ramp `10 s`; steady-state window `60 s`; error-rate ceiling `< 1 %` non-`200`; render deadline `30 s` |
| Steps | 1. Ramp to 20 req/s over 10 s with the 50/50 format split.<br>2. Hold the rate for 60 s.<br>3. Record achieved throughput, the non-`200` count, and the per-format response-time distribution. |
| Expected result | Achieved throughput over the 60 s window is ≥ 20 req/s — the arrival rate is met, not merely offered, with no queue growth across the window; non-`200` responses stay under 1 % of the window's requests; neither format's p95 exceeds 2× the other's, which is how a format-specific bottleneck shows up. |
| Status | Not run |
| Note | Threshold: sustained mixed-format rate over the window. Catches a format-specific render bottleneck. |
