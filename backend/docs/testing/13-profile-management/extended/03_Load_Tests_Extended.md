<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Profile management — Load Tests (Extended)

Same declared profile as the main file: **Throughput**.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account pool | 300 verified accounts `qa.load13.001@textery.test` … `qa.load13.300@textery.test`, password `Qa!Load2026` |
| Tokens | one access token per account, minted before the run and reused |
| Endpoint under load | `GET /api/v1/auth/me` |
| Throughput baseline | 200 profile reads/second sustained |
| Error-rate ceiling | < 1 % non-`200` responses over the measurement window |
| Pool configuration | `pool_size = 5`, `max_overflow = 10`, checkout timeout 30 s per process |
| Idle checkout baseline | checked-out connections sampled before the ramp (expected `0`–`1`) |
| Recovery window | 30 s after the database returns |
| Instance under test | one backend instance; ports and service names from `infra/.env` |

---

## 1. Recovery Shapes

### TC-13-LOAD-1.1e — The profile read recovers its rate after the database blips

| Field | Value |
|---|---|
| Description | Catches a pool that never returns to health after a blip — the failure mode that turns a ten-second database hiccup into an outage lasting until a restart. |
| Preconditions | The instance at steady state serving 200 `GET /api/v1/auth/me` per second; the checkout gauge sampled every 1 s throughout; the idle baseline recorded before the ramp. |
| Test data | Steady rate `200 req/s`; the Postgres service stopped for `10 s` mid-window, then started; recovery window `30 s`; error ceiling `< 1 %` measured **outside** the outage plus recovery window. |
| Steps | 1. Ramp to 200 req/s and hold for 30 s; record the achieved rate.<br>2. Stop the Postgres service for 10 s while the load continues.<br>3. Start Postgres again; keep the load running for 60 s.<br>4. Measure the achieved rate in each 5 s bucket after the restart, and sample the checkout gauge 60 s after the load stops. |
| Expected result | Within 30 s of the database returning, the achieved rate is back to >= 200 req/s and non-`200` responses fall back under 1 % — no permanent degradation and no `QueuePool limit … connection timed out` persisting past the recovery window; the application container never restarts; the checkout gauge in step 4 is back at the idle baseline (`0`–`1`). |
| Status | Not run |

### TC-13-LOAD-1.2e — A fleet reboot does not stampede the profile endpoint

| Field | Value |
|---|---|
| Description | Every open tab in the fleet re-reads this endpoint at boot, so unjittered client retries are a self-inflicted spike on the endpoint that just came back. |
| Preconditions | 300 simulated clients, each running the real client retry policy, all starting within the same 1 s after an endpoint outage; per-second arrival rate recorded at the backend. |
| Test data | 300 clients released simultaneously; endpoint answering `503` for the first 10 s then `200`; arrival-rate ceiling `200 req/s` in any 1 s bucket; jitter measured as the spread of retry timestamps within each retry generation. |
| Steps | 1. Take the endpoint down; hold the 300 clients' pages open.<br>2. Release all 300 at once; record every request's arrival timestamp at the backend.<br>3. Bucket the arrivals per second and read the peak bucket.<br>4. For each retry generation, compute the spread of its attempt timestamps.<br>5. Restore the endpoint to `200` and confirm each client shows an identity. |
| Expected result | No 1 s bucket exceeds the `200 req/s` ceiling, including the first second after release; within each retry generation the attempts are spread over a window at least as wide as the base delay — not clustered within a few tens of milliseconds; after step 5 all 300 clients show their identity without a manual reload. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's load-test baseline per `ProductSpecification/ExpectedLoad.md` |
| `the sustained page-view rate` | Request rate over the measurement window, driven at the load runner |
| `checked-out connections` | Pool checkout gauge |
| `the retries are spread` | Client backoff with jitter on the shared profile fetch |
