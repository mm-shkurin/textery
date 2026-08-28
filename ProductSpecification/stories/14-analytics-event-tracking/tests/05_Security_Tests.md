# Analytics Event Tracking — Security Tests

This story opens the product's **first write endpoint that accepts a request without a
token**. Everything else under `/api/v1` requires a Bearer token, so the scenarios below are
not routine hardening — they are the whole security surface of the change.

It also turns `GET /api/v1/auth/oauth/{provider}/start` into a write surface: five new query
parameters are bound onto the server-owned handshake row. That route is treated here as a
write endpoint, not a redirect.

Skipped as not applicable: NoSQL and LDAP injection (neither is in the stack), XXE (JSON
only), session fixation (JWT, no session cookie), CSRF (no cookie authentication — the token
travels in a header, so a cross-site form cannot carry it), and the cross-cutting concerns
tested globally (security headers, CORS, HTTPS, generic 401).

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Events endpoint | `POST /api/v1/analytics/events` — no token required |
| Register endpoint | `POST /api/v1/auth/register` |
| Handshake endpoint | `GET /api/v1/auth/oauth/{provider}/start` (`provider` = `yandex`) |
| Event body | `{"event_name": …, "visitor_id": …, "occurrence_key": …, "payload": {}, "degraded": false}` |
| Accepted event names | `SITE_VISITED`, `REGISTRATION_STARTED`, `EDITOR_OPENED` — every other name of the 12-name catalogue is refused |
| Account A (the caller) | `qa.sec.a@textery.test` / `Qa!SecA2026`, account id `4b1e9f27-3c60-4a58-9d12-7e05b8c34a91` |
| Account B (the victim) | `qa.sec.b@textery.test` / `Qa!SecB2026`, account id `a7c0d3e8-15b4-4f92-8e63-2d9a71f04b58`, owns document `d2f47a91-8c05-4b63-9a70-1e58c3d0f6b2` («Крыжовниковый синтез») |
| Visitor A | `11111111-2222-4333-8444-555555555555` |
| Visitor B | `66666666-7777-4888-8999-aaaaaaaaaaaa` |
| Occurrence keys | A fresh v4 UUID per report, unless the case reuses one deliberately |
| Error body shape | Exactly `{"error_code": "<CODE>", "message": "<fixed generic text>"}` — two keys, no `correlation_id`, no `detail`, never the rejected value |
| Error codes on the events route | `UNKNOWN_EVENT_NAME`, `INVALID_VISITOR_ID`, `INVALID_OCCURRENCE_KEY`, `INVALID_PAYLOAD` → `400`; `OCCURRENCE_KEY_CONFLICT` → `409`; `REQUEST_BODY_TOO_LARGE` → `413`; `RATE_LIMITED` → `429`; `INTERNAL_ERROR` → `500` |
| Bounds in force | `payload` ≤ 4096 bytes serialized, depth ≤ 8, ≤ 64 keys; request body ≤ 16384 bytes, on bytes actually read; each `utm_*` ≤ 200 code points after NFC; 120 events per 60 s per bucket |
| Stored tables | `analytics_events` (`id`, `sequence`, `event_name`, `visitor_id`, `occurrence_key`, `user_id`, `payload`, `degraded`, `event_time`); `accounts` (ten new nullable columns: five `utm_*`, `registration_ip`, `registration_country`, `device_type`, `operating_system`, `device_language`); `oauth_state_attribution` (`state_value` + five `utm_*`); `oauth_rate_limits` (`bucket_key`, `window_start`, `request_count`) |
| Bucket key | `analytics:` + the first 32 hex characters of `sha256(client_ip)` — a key space separate from OAuth's sign-in buckets |
| Sentinel value | `ZZQA-SENTINEL-7f31` — planted in turn in the database URL, the GeoIP credential, the bearer token, and a `utm_content` |

---

## 1. Forgery of the Event Stream

### TC-14-SEC-1.1 — A client cannot fabricate the events the business is measured by

| Field | Value |
|---|---|
| Description | The endpoint is anonymous and the four subscription names are declared in the catalogue for Stories 8 and 9. If the route accepted every declared name, anyone with a command line could write subscription activations into the table Story 15 computes revenue from. |
| Preconditions | No token presented. The `analytics_events` row count recorded before the run. |
| Test data | `event_name` in turn: `SUBSCRIPTION_ACTIVATED`, `GENERATION_STARTED`, `GENERATION_COMPLETED`, `LOGIN_SUCCESS`; `visitor_id` = Visitor A; a fresh occurrence key for each. |
| Steps | 1. `POST /api/v1/analytics/events` with `SUBSCRIPTION_ACTIVATED` and no `Authorization` header.<br>2. Repeat with `GENERATION_STARTED`.<br>3. Repeat with `GENERATION_COMPLETED`.<br>4. Repeat with `LOGIN_SUCCESS`.<br>5. Read every `analytics_events` row for Visitor A on a separate connection. |
| Expected result | All four answer `400` with exactly `{"error_code":"UNKNOWN_EVENT_NAME","message":"The event name is not one this endpoint accepts."}`; no body repeats the submitted name; zero `analytics_events` rows exist for Visitor A and the table's total row count is unchanged from the pre-run value. |
| Status | Not run |

### TC-14-SEC-1.2 — A signed-in caller cannot attach its events to another account

| Field | Value |
|---|---|
| Description | `user_id` is resolved from the token and never read from the body — the request schema does not declare it, so it is dropped at parse time rather than allowlisted. |
| Preconditions | Account A and account B both registered; account A holds a valid access token. |
| Test data | Body `{"event_name":"SITE_VISITED","visitor_id":"11111111-2222-4333-8444-555555555555","occurrence_key":"<fresh>","user_id":"a7c0d3e8-15b4-4f92-8e63-2d9a71f04b58"}` sent with account A's token. |
| Steps | 1. `POST /api/v1/analytics/events` with account A's Bearer token and the body above.<br>2. Read the stored row for that `occurrence_key` on a separate connection.<br>3. Count `analytics_events` rows whose `user_id` is account B's id. |
| Expected result | `204 No Content` with an empty body; the stored row's `user_id` is exactly `4b1e9f27-3c60-4a58-9d12-7e05b8c34a91` (account A), not `a7c0d3e8-…`; the count of rows owned by account B is 0. |
| Status | Not run |

### TC-14-SEC-1.3 — A caller cannot rewrite another visitor's history

| Field | Value |
|---|---|
| Description | The visitor identity is client-asserted and forgeable by construction. This case pins the blast radius — forging it can add noise, never alter or read someone else's rows. |
| Preconditions | Visitor A already has one stored `SITE_VISITED` row; a second browser holds Visitor B and account B's session. |
| Test data | The second caller posts `visitor_id` = Visitor A with a fresh `occurrence_key`, `event_name` = `EDITOR_OPENED`, and account B's token. |
| Steps | 1. Record every column of Visitor A's existing row (`id`, `sequence`, `event_name`, `user_id`, `payload`, `degraded`, `event_time`).<br>2. From the second browser, `POST /api/v1/analytics/events` carrying Visitor A's `visitor_id` and account B's token.<br>3. Re-read Visitor A's original row.<br>4. Read the newly stored row. |
| Expected result | `204 No Content`; Visitor A's original row is identical to step 1 in every column — no update, no `sequence` reassignment, no `event_time` change; the new row is a separate row whose `user_id` is account B's id (`a7c0d3e8-…`), never account A's; no response body reveals anything about the pre-existing row. |
| Status | Not run |

### TC-14-SEC-1.4 — A resource named in a payload confers nothing

| Field | Value |
|---|---|
| Description | The editor-opening event carries a document identifier on an anonymous-capable route with a free-form payload. The visitor identifier is declared untrusted in writing; identifiers inside the payload are not, so Story 15 would be entitled to join them to `documents` and attribute activity to the wrong owner. |
| Preconditions | Account B owns document `d2f47a91-8c05-4b63-9a70-1e58c3d0f6b2`; its `updated_at`, title and content recorded. No document has id `00000000-0000-4000-8000-000000000000`. |
| Test data | Body `{"event_name":"EDITOR_OPENED","visitor_id":"11111111-…-555555555555","occurrence_key":"<fresh>","payload":{"document_id":"d2f47a91-…"}}` with account A's token; then the same with the non-existent id. |
| Steps | 1. `POST /api/v1/analytics/events` with account A's token, naming account B's document in `payload`.<br>2. Repeat with `document_id` set to `00000000-0000-4000-8000-000000000000`.<br>3. Compare the two status lines, header sets (bar `Date`) and body bytes.<br>4. Read the two stored rows.<br>5. Re-read account B's document row and its `updated_at`. |
| Expected result | Both answer `204 No Content` with identical empty bodies and identical headers bar `Date` — the two responses are indistinguishable; both stored rows carry `user_id` = account A's id (`4b1e9f27-…`), never account B's; `payload` holds the id verbatim and nothing derived from it (no title, no owner, no timestamp); account B's document row, `updated_at` included, is unchanged. |
| Status | Not run |

---

## 2. Mass Assignment

### TC-14-SEC-2.1 — Server-owned fields cannot be set from the event body

| Field | Value |
|---|---|
| Description | `user_id`, `event_time`, `id` and `sequence` are deliberately absent from the request schema, so they are dropped at parse time rather than allowlisted; `sequence` is the total-order key Story 15 reads. |
| Preconditions | No token presented. The server's clock readable for comparison. |
| Test data | Body `{"event_name":"SITE_VISITED","visitor_id":"11111111-…-555555555555","occurrence_key":"<fresh>","user_id":"a7c0d3e8-…","event_time":"2000-01-01T00:00:00Z","id":"22222222-2222-4222-8222-222222222222","sequence":1}`. |
| Steps | 1. Record the server's current instant.<br>2. `POST /api/v1/analytics/events` with the body above and no `Authorization` header.<br>3. Read the stored row for that `occurrence_key` on a separate connection.<br>4. Compare `user_id`, `event_time`, `id` and `sequence` with the submitted values. |
| Expected result | `204 No Content`; the stored `user_id` is `NULL` (no token was sent), not `a7c0d3e8-…`; `event_time` is within seconds of the instant recorded in step 1, not `2000-01-01T00:00:00Z`, and keeps sub-second precision; `id` is server-minted and is not `22222222-…`; `sequence` is the table's next IDENTITY value and is not `1`. |
| Status | Not run |

### TC-14-SEC-2.2 — Server-owned fields cannot be set from the registration body

| Field | Value |
|---|---|
| Description | The register body's writable allow-list is exactly the three credential fields plus the five `utm_*`. `registration_ip`, `registration_country`, `device_type`, `operating_system` and `device_language` are server-derived and equally undeclared, so a body naming them is ignored — never a 400, never a 422. |
| Preconditions | `qa.sec.a@textery.test` not registered. Request sent with `Accept-Language: ru-RU,ru;q=0.9,en;q=0.8` and an ordinary desktop `User-Agent`. |
| Test data | The three credential fields plus `{"registration_ip":"203.0.113.7","registration_country":"US","device_type":"server","operating_system":"Plan 9","device_language":"zz-ZZ","is_verified":true,"failed_login_attempts":99,"created_at":"2000-01-01T00:00:00Z"}`. |
| Steps | 1. Record the server's current instant.<br>2. `POST /api/v1/auth/register` with the body and headers above.<br>3. Read the created `accounts` row on a separate connection.<br>4. Compare all eight named columns with the submitted values. |
| Expected result | `201 Created` — no `400`, no `422`; `registration_ip` is the address the server observed, not `203.0.113.7`; `registration_country` is the GeoIP result or `NULL`, not `US`; `device_type` and `operating_system` are derived from the sent `User-Agent`, not `server` / `Plan 9`; `device_language` is exactly `ru-ru` — lower-cased and canonical, derived from the highest-`q` `Accept-Language` tag, not `zz-ZZ`; `is_verified` is `false`; `failed_login_attempts` is `0`, not `99`; `created_at` is within seconds of step 1, not `2000-01-01T00:00:00Z`. |
| Status | Not run |

### TC-14-SEC-2.3 — The handshake binds only the five campaign parameters

| Field | Value |
|---|---|
| Description | This story is what makes the handshake route a write surface. Every other over-binding case here targets the two endpoints that were already writes. |
| Preconditions | `oauth_states` and `oauth_state_attribution` empty for this run; Yandex ID configured. |
| Test data | `GET /api/v1/auth/oauth/yandex/start?utm_source=vk&utm_medium=cpc&utm_campaign=spring2026&utm_content=banner_a&utm_term=диплом&state=FORGED-STATE&expires_at=2099-01-01T00:00:00Z&provider=vk`. |
| Steps | 1. Issue the request above.<br>2. Read the `state` value out of the `Location` header of the redirect.<br>3. Read the `oauth_states` row for that state.<br>4. Read the `oauth_state_attribution` row keyed on that state value. |
| Expected result | `302 Found`; the `state` in `Location` is a server-minted value, not `FORGED-STATE`; the `oauth_states` row's `state_value`, expiry and provider are all server-assigned — the expiry is the configured handshake TTL from now, not `2099-01-01T00:00:00Z`, and the provider is `yandex` (from the path), not `vk` (from the query); the `oauth_state_attribution` row holds exactly `utm_source=vk`, `utm_medium=cpc`, `utm_campaign=spring2026`, `utm_content=banner_a`, `utm_term=диплом`, and no other column of either row was written from the query. |
| Status | Not run |

---

## 3. Injection and Output Safety

### TC-14-SEC-3.1 — Hostile text in any stored field is stored, not executed, and never reflected

| Field | Value |
|---|---|
| Description | Stored verbatim is correct here — escaping belongs at Story 15's CSV and HTML sinks, and encoding on the way in would defeat it. What this asserts is that the values reach storage intact and never come back out in a response. |
| Preconditions | `qa.sec.a@textery.test` not registered. |
| Test data | `utm_source=' OR 1=1`; `utm_medium=<script>alert(1)</script>`; `utm_campaign==cmd\|'/c calc'!A1`; `utm_content=Отчёт'; DROP TABLE accounts; --`; `utm_term=<img src=x onerror=alert(1)>`. |
| Steps | 1. `POST /api/v1/auth/register` carrying the five payloads above in the body.<br>2. Read the full response body.<br>3. Re-read the created `accounts` row on a separate connection, in a separate session.<br>4. Compare each of the five columns with what was sent, byte for byte after NFC.<br>5. `SELECT count(*) FROM accounts` to confirm nothing was dropped. |
| Expected result | `201 Created` with the ordinary registration body — the same status and the same keys registration returns with no `utm_*` at all; the five stored columns are byte-identical after NFC to the submitted values, unescaped and untruncated: `<script>` is stored as `<script>`, and `=cmd\|'/c calc'!A1` keeps its leading `=`; the response body contains none of the five values; the `accounts` table still exists and its row count grew by exactly 1. |
| Status | Not run |

### TC-14-SEC-3.2 — Hostile text in a payload is stored, not transformed

| Field | Value |
|---|---|
| Description | Story 15 is promised verbatim storage for **both** the attribution values and the payload, and owes the escaping at its own sinks. An implementation that escapes payload on the way in leaves every scenario green and makes Story 15 double-encode. |
| Preconditions | No stored row for the occurrence key used. |
| Test data | `payload` = `{"a":"<img src=x onerror=alert(1)>","b":"' OR 1=1 --","c":"=cmd\|'/c calc'!A1","d":"строка & <b>жирный</b>"}`; `event_name` = `EDITOR_OPENED`; `visitor_id` = Visitor A. |
| Steps | 1. `POST /api/v1/analytics/events` with that payload and no token.<br>2. Read the full response body.<br>3. Read the stored row's `payload` on a separate connection.<br>4. Compare each of the four values with what was sent, byte for byte. |
| Expected result | `204 No Content` with an empty body; the stored `payload` is a `jsonb` object with exactly the four keys, each value byte-identical to what was sent — no `&lt;`, no `&amp;`, no added backslash escaping, no apostrophe prepended to the `=` value; no response body repeats any of the four values. |
| Status | Not run |

### TC-14-SEC-3.3 — A refusal never reflects what it rejected

| Field | Value |
|---|---|
| Description | The route reads the body as bytes and parses it itself precisely so a bad value returns the canonical envelope instead of Pydantic's `422`, which echoes the rejected input back on a route whose errors reach anyone. |
| Preconditions | No token presented. |
| Test data | (a) `event_name` = `<script>alert(1)</script>`; (b) `visitor_id` = `' OR 1=1 --`; (c) `occurrence_key` = `'; DROP TABLE analytics_events; --`. |
| Steps | 1. `POST /api/v1/analytics/events` with payload (a).<br>2. Repeat with payload (b).<br>3. Repeat with payload (c).<br>4. Read each full response body and header set.<br>5. Search each body for the submitted string and for internal markers. |
| Expected result | (a) `400` with exactly `{"error_code":"UNKNOWN_EVENT_NAME","message":"The event name is not one this endpoint accepts."}`; (b) `400` with `{"error_code":"INVALID_VISITOR_ID","message":"The visitor identifier is not a valid UUID."}`; (c) `400` with `{"error_code":"INVALID_OCCURRENCE_KEY","message":"The occurrence key is not a valid UUID."}`; each body carries exactly the two keys `error_code` and `message` and no `detail` array; no body contains any part of the submitted value, a file path, a module or class name, `Traceback`, `pydantic`, `sqlalchemy` or `asyncpg`. |
| Status | Not run |

### TC-14-SEC-3.4 — A refusal caused by an internal failure discloses nothing

| Field | Value |
|---|---|
| Description | The database-failure path is the single most likely place a driver message carrying the connection string, the table name or query fragments reaches an anonymous caller, and it had none. The three failure families with a disclosure assertion are the ones a client causes. |
| Preconditions | The database URL seeded with the sentinel `ZZQA-SENTINEL-7f31` (in the password or the application name). Fault injection available for the rate-limit adapter. |
| Test data | (a) the event store unreachable (database stopped); (b) the rate-limit adapter faulted to raise; (c) a caller already past 120 events per 60 s. |
| Steps | 1. Stop the database and `POST /api/v1/analytics/events` with an otherwise valid body.<br>2. Restore it, fault the rate-limit adapter to raise, and repeat.<br>3. Clear the fault, issue 121 events from one source, and read the 121st response.<br>4. Read the three full response bodies and header sets.<br>5. Search all three for the sentinel and for disclosure markers. |
| Expected result | (a) `500` with exactly `{"error_code":"INTERNAL_ERROR","message":"<fixed generic text>"}`; (b) refused rather than admitted — `429` with `{"error_code":"RATE_LIMITED","message":"Too many events from this source. Try again shortly."}`; (c) the same `429 RATE_LIMITED`; every body carries exactly the two keys; none contains `ZZQA-SENTINEL-7f31`, `Traceback`, `SELECT`, `INSERT`, `analytics_events`, `oauth_rate_limits`, `sqlalchemy`, `asyncpg`, `psycopg`, a `.py` path or an internal class name. |
| Status | Not run |

### TC-14-SEC-3.5 — Hostile text cannot forge a log entry

| Field | Value |
|---|---|
| Description | A payload value interpolated into a log message lets a caller write what looks like a second, attacker-authored record — the whole class this case closes. |
| Preconditions | Log capture armed and reset. The event recorder (`save_new`) faulted to raise. |
| Test data | `payload` = `{"note":"обычно\r\nWARNING: forged record: admin logged in\r\n%s %(x)s {0}"}`; `event_name` = `SITE_VISITED`; `visitor_id` = Visitor A. |
| Steps | 1. Reset the log capture and install the recorder fault.<br>2. `POST /api/v1/analytics/events` with the payload above.<br>3. Read every captured log record produced by that request.<br>4. Inspect how the payload value appears in each. |
| Expected result | Exactly one log record is emitted for that failure — not two, and none whose text begins `WARNING: forged record`; the payload value appears only as the value of a structured field, never interpolated into the message string, so the embedded `\r\n` produces no additional line and `%s`, `%(x)s` and `{0}` are neither expanded nor raise a formatting error; the record carries `event_name` and `visitor_id` as structured fields. |
| Status | Not run |

### TC-14-SEC-3.6 — Campaign parameters cannot forge a redirect or a header

| Field | Value |
|---|---|
| Description | The five values now arrive as query-string input on a route whose only output is a redirect header — the exact sink this class names. The existing redirect scenario asserts the campaign parameters are absent from it, using benign values. |
| Preconditions | Yandex ID configured; the route's baseline `Location` and header set recorded from a request carrying benign `utm_*`. |
| Test data | `utm_source=vk%0d%0aX-Injected:%20yes`; `utm_medium=cpc&redirect_uri=https://evil.example/steal`; `utm_campaign=spring%23fragment`; `utm_content=a%0d%0a%0d%0a<html>`; `utm_term=b&scope=admin`. |
| Steps | 1. `GET /api/v1/auth/oauth/yandex/start?…` with the five payloads above.<br>2. Read the status line, the full header set and the `Location` value.<br>3. Parse `Location` and enumerate its query keys.<br>4. Complete the handshake through `/callback` and read its own redirect back to the application. |
| Expected result | `302 Found` to the Yandex ID authorize URL — the visitor is still redirected; `Location`'s host is the provider's and its query keys are exactly the provider's expected set (`client_id`, `redirect_uri`, `response_type`, `scope`, `state`), with no `utm_*` key and no injected key; `redirect_uri` is the configured callback, not `https://evil.example/steal`, and `scope` is the configured scope, not `admin`; the response carries no `X-Injected` header and no header outside the baseline set; the callback's own redirect back to the application is byte-identical to the benign-parameter baseline. |
| Status | Not run |

---

## 4. Abuse Bounds

### TC-14-SEC-4.1 — An anonymous flood is bounded and fails closed

| Field | Value |
|---|---|
| Description | The second half is the one that matters: the story-wide rule «an analytics failure never changes the user's operation» must not be read as «admit everything when the limiter breaks», which would leave the busiest write path in the product with no bound at all. |
| Preconditions | `oauth_rate_limits` cleared for this source's bucket. Bound in force: 120 requests per 60 s per bucket. |
| Test data | 130 `SITE_VISITED` reports from one address inside one 60 s window, each with a fresh `occurrence_key`; then one report with the rate-limit adapter faulted to raise. |
| Steps | 1. Issue the 130 reports in sequence from one address, with no token.<br>2. Record the status of each.<br>3. Count the `analytics_events` rows stored for that visitor.<br>4. Fault the rate-limit adapter to raise and issue one further report.<br>5. Count the rows again. |
| Expected result | The first 120 answer `204 No Content`; requests 121–130 answer `429` with `{"error_code":"RATE_LIMITED","message":"Too many events from this source. Try again shortly."}`; exactly 120 rows are stored — none for the 10 refused; the request in step 4 is **refused, not admitted**, with the same `429 RATE_LIMITED` envelope, and the row count in step 5 is unchanged. |
| Status | Not run |

### TC-14-SEC-4.2 — Oversized and malformed bodies are refused before they are absorbed

| Field | Value |
|---|---|
| Description | The bound is enforced on bytes actually read, never on the declared `Content-Length` — a header claiming 10 is not a promise, and a route that trusts it absorbs whatever the caller really sends. Depth is separate from the byte cap because 4 KiB of `[[[[…]]]]` is under the size limit and still meets Python's decoder as a `RecursionError`, i.e. a 500 on a request that passed validation. |
| Preconditions | Bounds in force: request body ≤ 16384 bytes, `payload` ≤ 4096 bytes, depth ≤ 8, ≤ 64 keys. A byte counter armed on the server's request stream. |
| Test data | (a) a chunked body of 1 MiB with **no** `Content-Length`; (b) a `payload` nested 64 levels deep; (c) a `payload` whose single string value contains a NUL (`U+0000`). |
| Steps | 1. Send (a) with `Transfer-Encoding: chunked` and no `Content-Length`; record the bytes read at the point of refusal.<br>2. Send (b).<br>3. Send (c).<br>4. Read each status line and full body.<br>5. Count the `analytics_events` rows created by the three. |
| Expected result | (a) `413` with `{"error_code":"REQUEST_BODY_TOO_LARGE","message":"The request body is too large."}`, refused after reading just over 16384 bytes — not after the full 1 MiB; (b) and (c) each `400` with `{"error_code":"INVALID_PAYLOAD","message":"The request body is not acceptable."}`; none of the three answers `500`, and none surfaces a `RecursionError` or a `jsonb` driver error; zero rows were stored. |
| Status | Not run |

### TC-14-SEC-4.3 — Oversized and pathological headers are bounded, not parsed

| Field | Value |
|---|---|
| Description | Registration now parses two attacker-controlled **headers** into stored values, and user-agent parsing is a known backtracking surface. «Bounded» here means the parse gives up and stores nothing — **not** that the request is refused: a hostile `User-Agent` must not become a way to deny someone an account, and `/auth/register` has no header-driven refusal today (Governing Decision). |
| Preconditions | Three unregistered emails available. A healthy-registration latency baseline recorded. |
| Test data | (a) a `User-Agent` of 100 000 characters; (b) an `Accept-Language` carrying 5 000 comma-separated tags with `q` values; (c) a `User-Agent` fixture chosen against the chosen parser's known super-linear input, with a wall-clock ceiling equal to the registration budget. |
| Steps | 1. `POST /api/v1/auth/register` with header (a) and the first email.<br>2. Repeat with header (b) and the second email.<br>3. Repeat with header (c) and the third email, timing each request.<br>4. Read the three created `accounts` rows.<br>5. Inspect `device_type`, `operating_system` and `device_language` on each. |
| Expected result | All three answer `201 Created` — no `400`, no `413`, no `431`, no `500`; each request completes inside the registration latency budget recorded in Preconditions; on all three accounts `device_type`, `operating_system` and `device_language` are `NULL` — no truncated prefix, no partially-parsed token, no guessed default; the three accounts exist and are usable. |
| Status | Not run |

---

## 5. Personal Data

### TC-14-SEC-5.1 — Personal data is stored in exactly one place

| Field | Value |
|---|---|
| Description | The story's headline claim. If a distinctive address or campaign value also lives on an event row, in a log line or in a counter row, deleting the account no longer removes the person's data. |
| Preconditions | Log capture armed and reset. `qa.sec.a@textery.test` not registered. |
| Test data | Registration from address `198.51.100.77` carrying `utm_content=ZZQA-SENTINEL-7f31`; then every recorded event driven for that account and visitor. |
| Steps | 1. Register account A with the sentinel `utm_content` from the sentinel address.<br>2. Drive every recorded event for that account and visitor.<br>3. Read every `analytics_events` row for the visitor, including a text scan of `payload`.<br>4. Read every response body the caller received.<br>5. Read every captured log record.<br>6. Read every `oauth_rate_limits` row. |
| Expected result | `ZZQA-SENTINEL-7f31` and `198.51.100.77` each appear exactly once in the database — on the `accounts` row, as `utm_content` and `registration_ip` respectively; zero occurrences in any `analytics_events` column including a text scan of `payload`; zero occurrences in any response body; zero occurrences in any captured log record, where such a field appears as a fixed redaction token instead; zero occurrences in any `oauth_rate_limits` column. |
| Status | Not run |

### TC-14-SEC-5.2 — The abuse counters do not store the address in recoverable form

| Field | Value |
|---|---|
| Description | The bucket key is the visitor's address. That was harmless while the table held only sign-in attempts; once it keys every anonymous page view, this story's headline claim — that personal data lives on the account row and nowhere else — is either false or depends on a derivation nobody has stated. This case forces the decision. |
| Preconditions | `oauth_rate_limits` cleared. Requests issued from the sentinel address `198.51.100.77`. |
| Test data | 5 `SITE_VISITED` reports from `198.51.100.77`; the SHA-256 hex digest of that address computed independently for comparison. |
| Steps | 1. Issue the 5 reports from that address.<br>2. `SELECT bucket_key, window_start, request_count FROM oauth_rate_limits` directly.<br>3. Search every column for `198.51.100.77` and for its hex, decimal-integer and base64 encodings.<br>4. Compare `bucket_key` with the independently computed digest. |
| Expected result | `bucket_key` is exactly `analytics:` followed by the first 32 hex characters of `sha256("198.51.100.77")` — a one-way digest, not reversible without a secret; the raw address appears in no column, and neither does any encoding of it reversible without a secret; `window_start` is an epoch-second floor and `request_count` an integer, neither carrying an address; no column holds a `visitor_id`, a `user_id` or a URL. |
| Status | Not run |

### TC-14-SEC-5.3 — Deleting an account removes its personal data and bounds what is left

| Field | Value |
|---|---|
| Description | Analytics rows deliberately survive erasure with the account detached (`ON DELETE SET NULL`), because Story 15's cohort figures need them — so the erasure has to be complete on the account side and on the browser side both. A surviving frozen campaign set attaches verbatim to the next registration from that browser. |
| Preconditions | Account A registered from `198.51.100.77` via the marketing link, holding a frozen attribution set and a visitor identity in `localStorage`, with stored `analytics_events` rows. |
| Test data | Keys `textery.analytics.visitorId` and `textery.analytics.attribution`; account A's id and its event row ids recorded before deletion. |
| Steps | 1. Record account A's id, its `registration_ip`, and the ids of its `analytics_events` rows.<br>2. Complete the account-deletion flow.<br>3. Query `accounts` for that id.<br>4. Re-read the recorded `analytics_events` rows.<br>5. Read both `localStorage` analytics keys.<br>6. Register a new account from the same browser with no campaign parameters and read its five `utm_*`. |
| Expected result | The `accounts` row is gone, so `198.51.100.77` and every `utm_*` are absent from `accounts` entirely; every recorded `analytics_events` row still exists with `user_id` now `NULL` — not deleted, not reassigned; both `localStorage` analytics keys are absent (`null`); the new account's five `utm_*` are all `NULL` — in particular the deleted account's campaign does not reappear. |
| Status | Not run |

### TC-14-SEC-5.4 — The abuse counters do not become a permanent visitor log

| Field | Value |
|---|---|
| Description | Bucket-row lifetime must be bounded and named; without a prune, a table that keys every anonymous page view grows one row per address per window, forever. |
| Preconditions | `oauth_rate_limits` cleared. Window size 60 s. The clock controllable, or the windows genuinely elapsed. |
| Test data | 50 distinct source addresses reporting events across 5 consecutive 60 s windows — 250 analytics bucket rows created. |
| Steps | 1. Drive events from the 50 addresses across the 5 windows.<br>2. Count the analytics-prefixed `oauth_rate_limits` rows.<br>3. Advance past the retention horizon so all 5 windows have elapsed.<br>4. Run the prune.<br>5. Count the analytics-prefixed rows again. |
| Expected result | After step 2 there are exactly 250 analytics-prefixed rows; after step 5 every row whose `window_start` is older than the retention horizon is gone and the remaining analytics row count is at most the number of buckets in the live window (0 here); the count does not grow with the number of addresses seen historically. |
| Status | Not run |

### TC-14-SEC-5.5 — Pruning elapsed counters leaves live counters and the sign-in counters alone

| Field | Value |
|---|---|
| Description | An unqualified delete of the whole counter table satisfies TC-14-SEC-5.4 perfectly — while destroying every live-window count, the sole volume bound on the product's hottest write path and the one TC-14-SEC-4.1 requires to fail closed, and destroying OAuth's own sign-in counters, which share that table. The prune's predicate is scoped to this story's bucket key space, so OAuth's rows keep exactly the lifetime and the behaviour they have today. |
| Preconditions | `oauth_rate_limits` seeded with: `analytics:`-prefixed rows from an elapsed window; `analytics:`-prefixed rows in the current live window, one already at 120; OAuth sign-in rows for the same addresses, some elapsed and some live, one already at its own limit. |
| Test data | Every seeded row's `(bucket_key, window_start, request_count)` recorded before the prune. |
| Steps | 1. Record every seeded row.<br>2. Run the prune.<br>3. Re-read every row and compare with step 1.<br>4. Issue one more event from the address already at 120.<br>5. Issue one more sign-in start from the address already at the sign-in limit. |
| Expected result | Every `analytics:`-prefixed row from the elapsed window is gone; every `analytics:`-prefixed row in the live window is present with `request_count` unchanged; **every** OAuth sign-in row is present and unchanged, the elapsed ones included — the prune touched none of them; step 4 answers `429 RATE_LIMITED` (the live count survived the prune); step 5 is still refused exactly as it is today, with the same status and the same `error_code` it returns before this story. |
| Status | Not run |

### TC-14-SEC-5.6 — A dependency's credential never reaches a log or a response

| Field | Value |
|---|---|
| Description | A failing dependency is where a client library's exception text — URL, query string and token included — gets logged whole or wrapped into a response. |
| Preconditions | `GEOLOCATION_API_TOKEN` set to `ZZQA-SENTINEL-7f31` and `GEOLOCATION_API_URL` pointed at a stub. Log capture armed and reset. Four unregistered emails available. |
| Test data | The stub faulted in turn: connection refused, timeout, `500`, malformed body. |
| Steps | 1. Register once under each of the four failure modes.<br>2. Read each full response body.<br>3. Read every captured log record for each.<br>4. Search all bodies and records for `ZZQA-SENTINEL-7f31`.<br>5. Read the four created `accounts` rows. |
| Expected result | All four registrations answer `201 Created`; `ZZQA-SENTINEL-7f31` appears zero times in any response body and zero times in any captured log record — where the credential is referenced at all it is a fixed redaction token; each account's `registration_country` is `NULL` alongside a distinct resolver-failure signal, distinguishable from a legitimate NULL; no request exceeds the registration budget. |
| Status | Not run |

### TC-14-SEC-5.7 — A presented token never reaches a log or a response

| Field | Value |
|---|---|
| Description | This story opens the first route that accepts a request with *or* without a token, and drives refused-token shapes through it — each a natural place for a handler to log the rejected credential. The other sentinel cases seed data the *server* holds; this one seeds a credential the caller supplies. |
| Preconditions | Log capture armed and reset before each presentation. Account A registered. |
| Test data | Tokens carrying `ZZQA-SENTINEL-7f31` in their own text: (a) an expired access token; (b) a structurally malformed token; (c) a valid access token for account A. |
| Steps | 1. `POST /api/v1/analytics/events` with `Authorization: Bearer <expired sentinel token>`.<br>2. Repeat with the malformed sentinel token.<br>3. Repeat with the valid sentinel-bearing token.<br>4. Read all three full response bodies and every captured log record.<br>5. Search all of them for `ZZQA-SENTINEL-7f31`. |
| Expected result | (a) and (b) answer `401` in the canonical `{error_code, message}` shape with nothing stored — never downgraded to an anonymous `204`; (c) answers `204 No Content` and stores a row whose `user_id` is account A's id; `ZZQA-SENTINEL-7f31` appears zero times across the three response bodies and zero times in any captured log record; wherever the token is referenced in a record at all it is reduced to a fixed redaction token (e.g. `***`). |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `attempts to report a successful subscription` | `POST /api/v1/analytics/events` with `SUBSCRIPTION_ACTIVATED` |
| `naming the second as its owner` | `user_id` in the request body — a field the schema does not declare |
| `whose payload names a second account's document` | A document id belonging to another account, inside `payload` |
| `a handshake token, an expiry and a provider name` | `state`, `expires_at`, `provider` supplied as query parameters to `/oauth/{provider}/start` |
| `database syntax, markup and a spreadsheet formula` | `' OR 1=1`, `<script>alert(1)</script>`, `=cmd\|'/c calc'!A1` |
| `a fresh read returns exactly what was sent` | Byte-identical after NFC, re-read in a separate session |
| `line breaks, parameter separators, fragments and a second redirect target` | `%0d%0a`, `&`, `#`, a second `redirect_uri=` inside a `utm_*` value |
| `the payload value appears as data` | A structured log field, asserted as one record — never string-interpolated into the message |
| `the rate limiter's own store is unavailable` | Fault-inject the rate-limit adapter |
| `any part of the connection string` | Sentinel seeded into the database URL, asserted absent from every response body |
| `none is fully buffered before refusal` | Bytes read at the point of refusal, not `Content-Length` |
| `built to make its parser backtrack` | A `User-Agent` fixture chosen against the chosen parser's known super-linear input, with a wall-clock ceiling |
| `everything reported` | Captured log records, asserted on a fixed redaction token |
| `the abuse counter rows` | `oauth_rate_limits` — read directly, since the eraser deliberately does not touch it |
| `in recoverable form` | The raw address, and any encoding of it reversible without a secret |
| `the number of stored counter rows is bounded` | `oauth_rate_limits` row count after elapsed-window pruning |
| `sign-in counter rows` | The OAuth-start buckets that shared this table before this story |
| `a distinctive credential` | Sentinel value in the geolocation configuration |
| `a bearer token containing a distinctive sentinel` | Sentinel embedded in the token's own text, presented in the `Authorization` header |
