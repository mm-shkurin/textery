<!-- COPIED FILE. Source of truth: ProductSpecification/stories/05-manual-mode/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Manual input mode (non-AI document creation) — Load Tests

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`, Load Challenge
Profile). Unlike story #1, this story has no async/queue step — creation and save are
both plain synchronous request/response operations. The load risk is therefore pure
request-rate capacity on two simple endpoints, not queue depth or worker concurrency.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `document_type` `реферат`, `version` `1` |
| Idempotency key | `Idempotency-Key: 3f0c8a9e-2b41-4d77-9c6a-b5e1d2704f88` (a fresh UUID per virtual user) |
| Error body shape | `{"error_code": "<code>", "message": "<generic text>"}` |

The project's throughput baseline is vague in `ExpectedLoad.md` ("hundreds of
concurrent users"); it is pinned here as **200 virtual users, 150 req/s sustained,
60 s ramp + 300 s hold, error-rate ceiling 1 %**, and every case below uses those
numbers. Latency is recorded, not gated — `ExpectedLoad.md` explicitly declines a
latency SLO for this product.

---

## 1. Save Throughput

### TC-05-LOAD-1.1 — Document creation and save sustain the configured throughput baseline

| Field | Value |
|---|---|
| Description | Catches request-handling capacity regressions on the create/save path — an accidental synchronous DB lock or a missing connection pool only shows up under concurrency, never in a single-user test. |
| Preconditions | Backend and Postgres up (`GET /health` → `200 {"status": "ok", "failed_dependencies": []}`); account A exists and each virtual user holds a valid access token. |
| Test data | 200 concurrent virtual users; target 150 req/s across both endpoints; ramp 60 s, hold 300 s; error-rate ceiling 1 %; each user sends a fresh `Idempotency-Key` UUID; save payload `{"content": "<p>Абзац " + iteration + "</p>", "version": <current>}`. |
| Steps | 1. Ramp to 200 virtual users over 60 s.<br>2. Each user issues `POST /api/v1/documents` with `{"document_type": "реферат"}` and its own `Idempotency-Key`.<br>3. Each user then loops `PUT /api/v1/documents/{document_id}` with the incrementing `version` returned by the previous save, for the 300 s hold.<br>4. Record req/s, non-2xx rate and p95 latency over the hold window only. |
| Expected result | Sustained rate ≥ 150 req/s over the full 300 s hold; `POST` answers `201` (or `200` on an idempotency replay) and `PUT` answers `200`; non-2xx rate ≤ 1 %; no `500`; p95 latency recorded (observed ≤ 500 ms) and reported, not gated. |
| Status | Not run |

---

## 2. Concurrency Conflicts Under Load

### TC-05-LOAD-2.1 — Version-conflict saves stay within a bounded rate and do not degrade overall throughput

| Field | Value |
|---|---|
| Description | Catches an optimistic-concurrency implementation that serializes or locks more broadly than the single racing document, silently throttling unrelated saves. The `409`s must be exactly the ones the test induced — no unbounded tail. |
| Preconditions | Same as TC-05-LOAD-1.1, plus 5 pre-created shared documents (`document_type` `реферат`) that the racing subset will contend on, including document A1. |
| Test data | 200 virtual users, of which 20 (10 %) are the racing subset hammering the 5 shared documents with a deliberately stale `version` (always `1`); 180 non-racing users each on their own document; ramp 60 s, hold 300 s; expected induced `409` rate ≈ 10 % of total requests; non-racing baseline = TC-05-LOAD-1.1's 150 req/s and 1 % error ceiling. |
| Steps | 1. Ramp to 200 virtual users over 60 s as in TC-05-LOAD-1.1.<br>2. The 20 racing users repeatedly `PUT /api/v1/documents/{one of the 5 shared ids}` with `"version": 1`.<br>3. The 180 non-racing users run the create/save loop of TC-05-LOAD-1.1 on their own documents.<br>4. Over the 300 s hold, tally `409` responses split by subset, and measure req/s and latency for the non-racing subset separately. |
| Expected result | Every `409` carries `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}` and is attributable to the racing subset; zero `409` from the 180 non-racing users; the racing `409` rate stays at the induced ≈ 10 % and does not grow over the window; the non-racing subset still sustains ≥ 150 req/s scaled to its share with ≤ 1 % non-2xx and p95 within 10 % of TC-05-LOAD-1.1's recorded value. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `the configured throughput baseline of concurrent clients` | 200 concurrent clients, issuing `POST /api/v1/documents` then repeated `PUT /api/v1/documents/{document_id}` |
| `the endpoints sustain the configured request rate` | ≥ 150 requests/sec measured over the 300 s hold, across both endpoints |
| `the error rate stays within the configured ceiling` | non-2xx rate ≤ 1 % (excluding the deliberately induced 409s in scenario 2.1) measured over the load window |
| `deliberately racing saves against the same small set of documents` | 20 of the 200 clients repeatedly `PUT` the same 5 `document_id`s concurrently with stale `version` values |
| `version-conflict (409) responses` | count of `409` / `VERSION_CONFLICT` responses attributable to the racing subset |
| `the overall sustained request rate for non-conflicting saves is unaffected` | throughput/latency for the 180 non-racing clients compared against scenario 1.1's baseline |
