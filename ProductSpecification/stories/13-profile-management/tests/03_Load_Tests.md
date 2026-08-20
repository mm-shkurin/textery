# Profile management — Load Tests

The project's declared profile is **Throughput** (`ProductSpecification/ExpectedLoad.md`):
the binding constraint is request *rate*, not per-user data volume. This story converts a
zero-cost local token decode into a network call on effectively every authenticated page
view, which makes `GET /api/v1/auth/me` the highest-rate endpoint in the product — so the
story carries load scenarios even though it adds no queue, no external call and no scan.
That revises the interview's Performance paragraph; the reasoning is in
`13_ProfileManagement_Notes.md` § Load Considerations.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account pool | 300 verified accounts `qa.load13.001@textery.test` … `qa.load13.300@textery.test`, password `Qa!Load2026`, each with a distinct `name` (`Пользователь 001` …) |
| Tokens | one access token per account, minted once before the run and reused for the whole window |
| Endpoint under load | `GET /api/v1/auth/me` (read), `PATCH /api/v1/auth/me` (write) |
| Throughput baseline | 200 profile reads/second sustained (hundreds of concurrent users, ~1 read per page view) |
| Window | 60 s of steady state after a 10 s ramp (12 000 reads) |
| Error-rate ceiling | < 1 % non-`200` responses over the window |
| Pool configuration | SQLAlchemy defaults per process: `pool_size = 5`, `max_overflow = 10`, checkout timeout 30 s |
| Idle checkout baseline | checked-out connections sampled before the ramp (expected `0`–`1`) |
| Instance under test | one backend instance against the load database, ports from `infra/.env` |

---

## 1. Profile Read at Page-View Rate

### TC-13-LOAD-1.1 — The profile read sustains the product's page-view rate without exhausting the pool

| Field | Value |
|---|---|
| Description | Catches pool exhaustion and connection leaks on the endpoint every authenticated page now depends on — a leak here degrades documents and generations too, because they share the pool. |
| Preconditions | One backend instance running against the load database; the 300-account pool seeded and verified; one access token per account minted before the ramp; the pool checkout gauge sampled every 1 s from before the ramp until 60 s after the window closes. |
| Test data | Constant arrival rate `200 req/s`, ramp `10 s`, steady window `60 s` (12 000 requests); accounts drawn round-robin from the pool; error ceiling `< 1 %`; pool `5 + 10 overflow`. |
| Steps | 1. Sample the idle checked-out-connection count.<br>2. Ramp to 200 req/s over 10 s.<br>3. Hold 200 req/s for 60 s, recording every response status, body and duration.<br>4. Stop the load, wait 60 s, and sample the checkout gauge again. |
| Expected result | The measured completed rate over the window is >= 200 req/s (>= 12 000 responses, no backlog draining at the end); every `200` body's `email` equals the account whose token was sent — zero cross-account bodies; non-`200` responses are < 1 % of the total; **zero** `QueuePool limit … connection timed out` errors and zero `500`s from a checkout timeout; the checkout gauge in step 4 is back at the step-1 idle baseline (`0`–`1`), not stuck at 15. |
| Status | Not run |
| Note | `200 req/s` is this suite's stated baseline; if `ExpectedLoad.md` later fixes a different figure, update this threshold rather than the runner. |

### TC-13-LOAD-1.2 — The per-request database cost this scenario is sized against cannot drift silently

| Field | Value |
|---|---|
| Description | Pinned at **two**, not one (`endpoints.md`): the container opens one session per dependency and the account-existence check is itself a dependency, so the existence check and the profile read run on separate sessions — two selects, two simultaneous checkouts, two liveness round-trips per request. This is what stops TC-13-LOAD-1.1's sizing premise from silently becoming false in either direction. |
| Preconditions | One authenticated account; a `before_cursor_execute` listener attached to the engine, per the idiom of `test_generation_storage_cas_shape.py`; the capture cleared immediately before the request. |
| Test data | One `GET /api/v1/auth/me` with a valid access token; pinned count `2`; statement pattern `SELECT … FROM accounts WHERE accounts.id = …`. |
| Steps | 1. Clear the statement capture.<br>2. Issue exactly one `GET /api/v1/auth/me`.<br>3. Count captured statements matching `FROM accounts WHERE … id`.<br>4. Record the peak simultaneous checkouts during that single request. |
| Expected result | The count in step 3 is exactly `2` — the assertion fails at `1` and at `3` alike; the peak simultaneous checkouts in step 4 is `2`. |
| Status | Not run |
| Note | Collapsing the two to one is an open ADR due before the backend scenarios; when it lands, the pinned count and TC-13-LOAD-1.1's sizing both change together. |

---

## 2. Rename Under Read Load

### TC-13-LOAD-2.1 — Renames do not stall the read path

| Field | Value |
|---|---|
| Description | Catches a rename that takes a lock or holds a connection long enough to eat the read path's headroom — the write is rare, the read is on every page, and they share one pool. |
| Preconditions | The same instance, account pool and tokens as TC-13-LOAD-1.1; every account starts with a set name. |
| Test data | Read arrival rate `200 req/s` for 60 s after a 10 s ramp; a `5 %` write share — `10 PATCH /api/v1/auth/me` per second with body `{"name": "Пользователь <n>-<iteration>"}`; error ceiling `< 1 %` across both paths. |
| Steps | 1. Ramp the read load to 200 req/s.<br>2. Hold 200 req/s of reads for 60 s while injecting 10 renames/second.<br>3. Record the achieved read rate, the read status histogram and the write status histogram. |
| Expected result | The completed **read** rate over the window is still >= 200 req/s (>= 12 000 reads), no worse than the read-only run of TC-13-LOAD-1.1; combined non-`2xx` responses are < 1 % of the total; no `PATCH` blocks a read behind a row or table lock — zero pool checkout timeouts. |
| Status | Not run |

### TC-13-LOAD-2.2 — The refusal paths return their connections too

| Field | Value |
|---|---|
| Description | Every other checkout assertion in this spec sits behind a successful driver or a database that is down. A refusal aborts the request **after** the account-existence dependency has already checked out its session — at two checkouts per request against a pool of five plus ten overflow, a leak on that branch exhausts within a burst and takes documents and generations down with it. |
| Preconditions | One backend instance; the checkout gauge sampled every 1 s from before the ramp until 60 s after the window; the idle baseline recorded. |
| Test data | 60 s window at `200 req/s`, split evenly across four refusal drivers: (a) `GET /me` with a forged token → `401`; (b) `PATCH /me` with `{"name": "а" × 300}` → `400 NAME_INPUT_TOO_LARGE`; (c) `PATCH /me` with `{"name": "я" × 61}` → `400 INVALID_NAME`; (d) `PATCH /me` with a 10 MiB body → `413 REQUEST_BODY_TOO_LARGE`. |
| Steps | 1. Sample the idle checked-out-connection count.<br>2. Ramp and hold 200 req/s of the four refusals for 60 s.<br>3. Stop the load, wait 60 s, sample the gauge again.<br>4. Immediately issue 50 ordinary `GET /api/v1/auth/me` requests with valid tokens. |
| Expected result | Every response in step 2 carries its expected refusal status (no `500`s); the gauge in step 3 is back at the step-1 idle baseline (`0`–`1`), never pinned at the 15-connection ceiling; all 50 requests in step 4 answer `200` with zero `QueuePool limit … connection timed out`. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's load-test baseline setup per `ProductSpecification/ExpectedLoad.md` |
| `the product's concurrency target` | Hundreds of concurrent users (`ExpectedLoad.md`) |
| `the sustained page-view rate` | Request rate over the measurement window, driven at the load runner |
| `reads their profiles` | `GET /api/v1/auth/me` with a valid access token |
| `no request fails waiting for a database connection` | No pool checkout timeout; SQLAlchemy default 5 + 10 overflow per process |
| `checked-out connections return to their idle baseline` | Pool checkout gauge sampled after the window |
| `the number of account selects issued` | `before_cursor_execute` capture, idiom of `test_generation_storage_cas_shape.py` |
| `the error rate ceiling` | The project's configured load error-rate ceiling |
