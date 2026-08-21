> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — Load Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Endpoints under load | `POST /api/v1/documents`, `PUT /api/v1/documents/{document_id}` |
| Baseline (from `03_Load_Tests.md`) | 200 virtual users, 150 req/s sustained, error-rate ceiling 1 % |
| Burst | 400 virtual users, 300 req/s for 60 s |
| Recovery window | 120 s after the burst subsides |

## 1. Recovery After a Load Spike

### TC-05-LOAD-EXT-1.1 — Throughput recovers after a burst subsides

| Field | Value |
|---|---|
| Description | Catches a system that survives the spike but does not come back — a saturated connection pool, an unbounded retry queue, or a backlog that keeps the error rate elevated long after the traffic is gone. |
| Preconditions | Backend and Postgres up (`GET /health` → `200 {"status": "ok", "failed_dependencies": []}`); the baseline run of TC-05-LOAD-1.1 has been recorded (150 req/s, ≤ 1 % non-2xx, p95 latency value). |
| Test data | Burst: 400 virtual users at 300 req/s for 60 s (double the baseline); then drop back to 200 users / 150 req/s; recovery window 120 s; success criterion = non-2xx rate ≤ 1 % and p95 within 10 % of the recorded baseline. |
| Steps | 1. Run the baseline load of TC-05-LOAD-1.1 for 120 s and record req/s, non-2xx rate and p95.<br>2. Ramp to the 400-user / 300 req/s burst and hold it 60 s.<br>3. Drop back to the baseline rate.<br>4. Measure req/s, non-2xx rate and p95 in 30 s buckets across the 120 s recovery window.<br>5. Poll `GET /health` throughout. |
| Expected result | Within the 120 s recovery window the non-2xx rate is back to ≤ 1 % and the sustained rate is ≥ 150 req/s, with p95 within 10 % of the step-1 baseline; no bucket after the first 30 s still shows an elevated error rate; no `500` persists past the burst; `GET /health` never reports a failed dependency and the process does not restart. |
| Status | Not run |
