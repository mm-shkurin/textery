> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — Security Tests (Extended)

Shared test data is inherited from `05_Security_Tests.md` (the tokenless ingest route
`POST /api/v1/analytics/events` and its `event_name` / `visitor_id` / `occurrence_key` /
`payload` / `degraded` body, the canonical error envelope `{"error_code","message"}`, the
extended routes `POST /api/v1/auth/register` and `GET /api/v1/auth/oauth/{provider}/start`,
the 200-code-point `utm_*` bound, and the rule that every persistence assertion is re-read in
a **fresh session**). Cases that need their own values name them below.

---

## 1. Token Handling on the Anonymous Route

### TC-14-SEC-EXT-1.1 — Every unusable token shape is refused identically

| Field | Value |
|---|---|
| Description | This is the product's only tokenless write, so "no token" is a legitimate state — which makes downgrading a *bad* token to it the standing risk. A refusal that differs by shape also turns the route into an oracle telling an attacker why a stolen token failed. |
| Preconditions | A live account exists (so a valid token is obtainable for contrast). No events stored for the test `visitor_id`. |
| Test data | Five `Authorization: Bearer <t>` values: (a) an expired access token, (b) a valid refresh token, (c) a token whose type claim is `unknown`, (d) a structurally malformed string `abc.def`, (e) a well-formed access token signed with a key other than the configured secret. One `visitor_id` V, five distinct `occurrence_key` UUIDs, `event_name` = `SITE_VISITED`. |
| Steps | 1. `POST /api/v1/analytics/events` with header (a).<br>2. Repeat with (b), (c), (d), (e), each with its own `occurrence_key`.<br>3. Compare the five status codes, `error_code` values, messages and response headers pairwise.<br>4. In a fresh session, count `analytics_events` rows for `visitor_id` V. |
| Expected result | All five answer `401` with the canonical envelope. All five bodies are byte-identical — `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}` byte for byte (`security/current_owner.py` raises one `_unauthorized()` for missing, wrong-scheme, empty, expired, tampered, wrong-type and deleted-account alike); no body names the token, its expiry, its type, or which check failed. Step 4 counts **0** rows: no request was recorded, anonymously or otherwise. |
| Status | Not run |

### TC-14-SEC-EXT-1.2 — An empty or malformed authorization header is refused, not ignored

| Field | Value |
|---|---|
| Description | Silent downgrade is the failure to guard against: treating an unusable header as «no header» would let a caller with a revoked token keep writing, indistinguishably from a visitor who never signed in. |
| Preconditions | No events stored for the test `visitor_id`. |
| Test data | Header H1: `Authorization:` with an empty value. Header H2: `Authorization: Basic dXNlcjpwYXNz` — a scheme other than `Bearer`. Contrast request H0: the header entirely absent. One `visitor_id` V, three distinct `occurrence_key` UUIDs, `event_name` = `SITE_VISITED`. |
| Steps | 1. `POST /api/v1/analytics/events` with header H1.<br>2. `POST /api/v1/analytics/events` with header H2.<br>3. `POST /api/v1/analytics/events` with no `Authorization` header at all (H0).<br>4. In a fresh session, read all `analytics_events` rows for `visitor_id` V. |
| Expected result | Steps 1 and 2 both answer `401` with the canonical envelope, identical to each other and to TC-14-SEC-EXT-1.1's refusals. Step 3 answers `204`. Exactly **one** row exists for V — the H0 request's, with `user_id IS NULL`; neither H1 nor H2 produced a row, so neither was downgraded to an anonymous event. |
| Status | Not run |

The failure to guard against here is silent downgrade: treating an unusable header as
«no header» would let a caller with a revoked token keep writing, indistinguishably from a
visitor who never signed in.

---

## 2. Claims a Client Should Not Be Able to Make

### TC-14-SEC-EXT-2.1 — The degraded marker cannot be used to hide from the counts

| Field | Value |
|---|---|
| Description | `degraded` exists so Story 15 can exclude an inflated per-page-load population, not as a privilege. A client asserting it must gain nothing — no attribution difference, no rate-limit exemption. |
| Preconditions | No session. Rate limit for this route: 120 requests per 60 s per `client_source()` bucket. No events stored for either visitor. |
| Test data | Visitor V1 sends `"degraded": true` while in fact holding a persisted identity; visitor V2 sends `"degraded": false` from the same source. Both send `event_name` = `SITE_VISITED` with their own `occurrence_key` UUIDs. A registration carried out from the degraded browser with `utm_source=vk&utm_campaign=spring2026` frozen. |
| Steps | 1. `POST /api/v1/analytics/events` as V1 with `"degraded": true`.<br>2. `POST /api/v1/analytics/events` as V2 with `"degraded": false`.<br>3. In a fresh session, read both rows' `degraded`, `visitor_id` and `user_id`.<br>4. Register from the degraded browser and read the account's five `utm_*` columns.<br>5. From the degraded client, send events past the 120-per-60-s bound in one window. |
| Expected result | Both answer `204`. V1's row stores `degraded = true` and V2's `degraded = false` — the marker is recorded as sent, in its own column, not inside `payload`. V1's `visitor_id` is stored exactly as sent, unchanged by the marker. Step 4's account stores `utm_source` = `vk` and `utm_campaign` = `spring2026` — identical to the same registration from a non-degraded browser. Step 5 answers `429` with `{"error_code":"RATE_LIMITED",…}` at the same request number as an undegraded client: the marker buys no extra budget. |
| Status | Not run |

The marker exists so Story 15 can exclude an inflated population, not as a privilege. This
pins that a client asserting it gains nothing beyond being excluded from a count.

### TC-14-SEC-EXT-2.2 — Occurrence keys cannot be used to probe what already exists

| Field | Value |
|---|---|
| Description | The unique index is `(visitor_id, occurrence_key)`. Were it global, a `409` on someone else's key would answer "this occurrence exists", turning a client-minted UUID into an enumeration oracle over other visitors' history. |
| Preconditions | No session. Visitor V1 has already recorded a `SITE_VISITED` under key K. |
| Test data | Known key K (v4 UUID) already stored for V1; probing visitor V2 (different `visitor_id`); a fresh, never-used key F for the control request; `event_name` = `SITE_VISITED` for both V2 requests. |
| Steps | 1. As V2, `POST /api/v1/analytics/events` with key K; record status, body, headers and elapsed time.<br>2. As V2, `POST /api/v1/analytics/events` with the fresh key F; record the same.<br>3. Compare the two responses field by field.<br>4. In a fresh session, read all rows for K and confirm V1's row is untouched. |
| Expected result | Both answer `204` with an empty body and the same headers — the reused key is indistinguishable from a fresh occurrence, and no `409` is returned. Two rows exist for K, one per `visitor_id`; V1's row keeps its original `id`, `event_name`, `payload` and `event_time`. Nothing in either response reveals that K was already in use. |
| Status | Not run |

---

## 3. Input Volume

### TC-14-SEC-EXT-3.1 — Attribution values at and past their bound behave as documented

| Field | Value |
|---|---|
| Description | The 200-code-point bound is what stops an unbounded string reaching the store; on this route it is enforced by **discarding**, not by refusing. An attacker must not be able to deny a registration by appending to a marketing link. |
| Preconditions | Three unregistered accounts: `qa.bound.at@textery.test`, `qa.bound.over@textery.test`, `qa.bound.huge@textery.test`. |
| Test data | Registration AT: `utm_campaign` = the letter `a` repeated exactly 200 times (200 code points, after NFC). Registration OVER: `utm_campaign` = `a` × 201. Registration HUGE: `utm_campaign` = `a` × 1 000 000. Each also sends `utm_source: "vk"`. Control: the same registration with no `utm_*` at all. |
| Steps | 1. `POST /api/v1/auth/register` as AT.<br>2. `POST /api/v1/auth/register` as OVER.<br>3. `POST /api/v1/auth/register` as HUGE.<br>4. In a fresh session, read each account's five `utm_*` columns and the stored code-point length of each non-NULL value.<br>5. Compare all three responses' status codes, body shapes and `error_code` sets with the control registration's. |
| Expected result | AT stores `utm_campaign` at exactly 200 code points and `utm_source` = `vk` — the bound is inclusive. OVER and HUGE store NULL in **all five** columns; no value of length 200 (or any other truncated length) is stored for them, so nothing was truncated-and-kept. All three registrations succeed with the same status code and body shape as the control, and no new `error_code` appears — no volume of attribution text refuses a registration. |
| Status | Not run |

The bound is still a security bound — it is what stops an unbounded string reaching the
store — but on this route it is enforced by **discarding**, not by refusing. The last line is
the assertion: an attacker who wants to deny registration cannot do it by appending to a
marketing link.

Note what is deliberately *not* added: `/auth/register` carries no request-body cap today
(only `avatar_router.py` does), and this story does not give it one — that would be precisely
the new refusal reason the Governing Decision forbids. The exposure to an enormous register
body is therefore exactly what it is today, neither better nor worse; the bound's only job
here is that an over-long value is never **stored**.

### TC-14-SEC-EXT-3.2 — A body that is not JSON at all is refused without disclosing internals

| Field | Value |
|---|---|
| Description | The route reads the body as bytes and parses it itself (`analytics_router._parsed`), precisely so a body that is not JSON answers the product's own envelope instead of FastAPI's `{"detail": …}` 422, which echoes the rejected input back on an endpoint anyone with a socket can reach. This case pins both halves: the canonical shape, and that it discloses nothing. |
| Preconditions | None. No events stored for the test `visitor_id`. |
| Test data | Body B1: `{` sent as `Content-Type: application/json`. Body B2: `SITE_VISITED please` sent as `Content-Type: text/plain`. Body B3: an empty body with `Content-Type: application/json`. |
| Steps | 1. `POST /api/v1/analytics/events` with B1.<br>2. `POST /api/v1/analytics/events` with B2.<br>3. `POST /api/v1/analytics/events` with B3.<br>4. Read each full response body and every response header.<br>5. In a fresh session, count `analytics_events` rows created during the run. |
| Expected result | All three are refused `400` with the canonical envelope `{"error_code": "INVALID_PAYLOAD", "message": "The request body is not acceptable."}`, identical across the three; none answers `2xx`, and none answers FastAPI's `{"detail": …}` shape. No response body or header contains a file path, a module or class name, a stack frame, a SQL fragment, a library version, or the rejected bytes echoed back. Step 5 counts **0** new rows. |
| Status | Not run |

`endpoints.md` § "Residual this contract does not own" still describes the pre-implementation
plan, in which this body fell through to FastAPI's 422. The route as built closes that
residual for its own path by parsing the body itself — the 26 other endpoints are unchanged,
which is what made the residual app-wide in the first place. This case asserts the shipped
behaviour, and the part it always owned: whatever the shape, it discloses nothing.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `signed by the wrong key` | JWT signed with a key other than the configured secret |
| `indistinguishable from one another` | Identical status and body across all refusals |
| `marking itself as unable to store its identity` | `degraded: true` sent by a client that in fact persisted its identity |
| `an occurrence already recorded by another visitor` | Reuse of a known `occurrence_key` across `visitor_id` values |
