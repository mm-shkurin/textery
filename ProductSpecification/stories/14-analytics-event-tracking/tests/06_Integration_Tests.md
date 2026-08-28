# Analytics Event Tracking — Integration Tests

Two integrations: the geolocation dependency this story introduces on the registration path,
and the existing OAuth handshake, which this story extends so a provider-created account is
not born without attribution.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Registration endpoint | `POST /api/v1/auth/register` — `201` on success; response set unchanged by this story (`201 / 400 / 409 / 500`) |
| OAuth start | `GET /api/v1/auth/oauth/{provider}/start` — `302 / 404 / 500`, no `400`; `provider=yandex` |
| OAuth callback | `GET /api/v1/auth/oauth/{provider}/callback` |
| Registrant R1 | `qa.geo001@textery.test` / `Qa!Geo2026` |
| Registrant R2 | `qa.geo002@textery.test` / `Qa!Geo2026` |
| Registrant R3 | `qa.geo003@textery.test` / `Qa!Geo2026` |
| OAuth visitor P1 | provider subject `yandex-sub-7f21c3a4`, email `qa.oauth001@textery.test` |
| OAuth visitor P2 | provider subject `yandex-sub-6b90d1e5`, email `qa.oauth002@textery.test` |
| Public address under test | `203.0.113.44`, resolving to country `RU` |
| Proxy chain | `X-Forwarded-For: 203.0.113.44, 198.51.100.7, 10.0.0.3`; `TRUSTED_PROXY_HOPS=1`, `MAX_FORWARDED_FOR_LENGTH=1024` |
| Campaign set | `utm_source=vk`, `utm_medium=cpc`, `utm_campaign=spring2026`, `utm_content=banner_a`, `utm_term=диплом` |
| Account columns written | `registration_ip`, `registration_country`, `device_type`, `operating_system`, `device_language`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` (all `TEXT NULL`, migration `d6e7f8a9b0c1`) |
| Handshake parking row | `oauth_state_attribution(state_value, utm_source, utm_medium, utm_campaign, utm_content, utm_term)`, keyed on the state value, deleted as the callback reads it |
| Handshake lifetime | `STATE_TTL_MINUTES = 10` (`domain/src/auth/oauth_state.py`); expiry evaluated as `moment >= expires_at` |
| Geolocation port | `Geolocation.country_of(ip)`; `HttpGeolocation` never raises and never retries; `GEOLOCATION_TIMEOUT_SECONDS` default `1.5` s total |
| Geolocation unset | `GEOLOCATION_API_URL` blank → `NullGeolocation`, `registration_country` NULL, one startup record |
| Emission allowance | `RECORDING_TIMEOUT_SECONDS = 2.0` (`server_event_recorder.py`) |
| Registration budget | the endpoint's healthy-dependency duration; the geolocation call must stay inside it |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}`; `correlation_id` added on 5xx only. **No new `error_code` on either extended route.** |
| Event names emitted here | `REGISTRATION_COMPLETED`, `LOGIN_SUCCESS` |

---

## 1. Geolocation

### TC-14-INT-1.1 — A located address is stored as its country

| Field | Value |
|---|---|
| Description | The one path where the dependency actually contributes a value; without it every other case in this section could pass with a port that always answers nothing. |
| Preconditions | Geolocation port configured and answering; `qa.geo001@textery.test` not registered. |
| Test data | Port fake resolving `203.0.113.44` to `RU`; registrant R1; request arriving from `203.0.113.44`. |
| Steps | 1. Configure the port fake to answer `RU` for `203.0.113.44`.<br>2. `POST /api/v1/auth/register` for R1 from that address.<br>3. Read the `accounts` row for R1 in a separate DB session. |
| Expected result | The registration answers `201`; the row's `registration_country` is exactly `RU` (upper-cased, two letters) and `registration_ip` is `203.0.113.44`; the port fake recorded exactly one call, with `203.0.113.44` as its argument. |
| Status | Not run |

### TC-14-INT-1.2 — Every failure mode leaves registration whole and the country unset

| Field | Value |
|---|---|
| Description | Three different shapes of dependency failure must be indistinguishable to the registering user: the account is created and only the marketing column is missing. A 4xx, a 5xx and unreadable output are the three ways a real lookup service breaks. |
| Preconditions | R1, R2 and R3 not registered; the log collector attached. |
| Test data | Port fake raising the adapter's refusal (4xx) for R1, a server error (5xx) for R2, and a malformed/unparseable response for R3. |
| Steps | 1. Set the port fake to refuse the request; register R1.<br>2. Set it to answer a server error; register R2.<br>3. Set it to answer something unreadable; register R3.<br>4. Read the three `accounts` rows in a separate DB session.<br>5. Read the log records emitted during the three registrations. |
| Expected result | All three registrations answer `201` with the same body they return with a healthy dependency — no new `error_code`, no 5xx; all three rows carry `registration_country` NULL while `registration_ip`, `device_type`, `operating_system` and `device_language` are still populated; each failure produced exactly one structured log record naming the failure's type only, with no URL, token or IP in it. |
| Status | Not run |

### TC-14-INT-1.3 — A failing dependency is asked once, not repeatedly

| Field | Value |
|---|---|
| Description | TC-14-INT-1.2 asserts the *outcome* of each failure mode is identical; it never counts the calls. An adapter whose default policy retries a server error three times passes it, and multiplies the configured timeout — which is what breaks the registration budget. |
| Preconditions | R1 and R2 not registered; the port fake's call counter reset before each registration; healthy-dependency registration duration recorded as the budget. |
| Test data | Port fake answering a server error for R1, then refusing the request for R2; `GEOLOCATION_TIMEOUT_SECONDS=1.5`. |
| Steps | 1. Record the registration duration against a healthy port.<br>2. Reset the counter, set the fake to a server error, register R1 and time it.<br>3. Reset the counter, set the fake to refuse the request, register R2 and time it.<br>4. Read both call counts and both `accounts` rows. |
| Expected result | The call count is exactly `1` per registration in both cases — never 2, 3 or 4; both registrations answer `201` within the step-1 duration plus one 1.5 s timeout, never a multiple of it; both rows carry `registration_country` NULL. |
| Status | Not run |

### TC-14-INT-1.4 — A dependency that does not answer is abandoned, not waited on

| Field | Value |
|---|---|
| Description | The shape that actually hangs a request: the lookup service accepts the connection and then never answers, so a connect-only timeout never fires. Registration must give up on its own clock. |
| Preconditions | R1 not registered; port fake accepting the connection and never answering; the healthy-dependency registration duration recorded. |
| Test data | Hanging port fake; `GEOLOCATION_TIMEOUT_SECONDS=1.5`; the client's own deadline set to the registration budget. |
| Steps | 1. Install the hanging port fake.<br>2. `POST /api/v1/auth/register` for R1 and measure the elapsed time.<br>3. Read R1's `accounts` row in a separate session.<br>4. Abort a second identical registration client-side before it answers, then query `accounts` for that email 30 s later. |
| Expected result | Step 2 answers `201` within the healthy-dependency duration plus 1.5 s — the request is never held for the socket's own lifetime; R1's `registration_country` is NULL while the other four technical columns are populated; after step 4 no `accounts` row exists for the aborted registration's email, and none appears later. |
| Status | Not run |

### TC-14-INT-1.5 — The address the dependency is asked about is the caller's, not a proxy's

| Field | Value |
|---|---|
| Description | The extraction is the one already used for sign-in abuse bounds, whose own documentation calls it a best-effort measure that no security invariant rests on. This story makes its output durable business data, so which hop is trusted stops being a detail. |
| Preconditions | `TRUSTED_PROXY_HOPS=1`; the request reaches the app through the deployment's single nginx hop; R1 not registered. |
| Test data | `X-Forwarded-For: 203.0.113.44, 198.51.100.7, 10.0.0.3`; port fake answering `RU` for `203.0.113.44` and `NL` for `198.51.100.7`. |
| Steps | 1. Send `POST /api/v1/auth/register` for R1 through the proxy chain above.<br>2. Read the argument the port fake was called with.<br>3. Read R1's `registration_ip` and `registration_country` in a separate session. |
| Expected result | The port fake was asked about exactly the address `TRUSTED_PROXY_HOPS=1` designates (the last hop before our own proxy) and about nothing else; `registration_ip` holds that same address character for character; `registration_country` is the country the fake returned for it, not `NL` and not the string `unknown`. |
| Status | Not run |

---

## 2. OAuth Sign-In

### TC-14-INT-2.1 — Attribution carried into the handshake reaches the created account

| Field | Value |
|---|---|
| Description | The account is created inside the callback, two redirects from anything a client can put in a body; without carrying the set through the handshake every provider sign-up registers with NULL attribution. |
| Preconditions | `yandex-sub-7f21c3a4` has no account; the provider is driven through its existing fake. |
| Test data | `GET /api/v1/auth/oauth/yandex/start?utm_source=vk&utm_medium=cpc&utm_campaign=spring2026&utm_content=banner_a&utm_term=диплом`; the state value minted by that call. |
| Steps | 1. Call `/start` with the five parameters and capture the `302` and its state value.<br>2. Read the `oauth_state_attribution` row for that state value.<br>3. Complete the callback for P1 so the account is created.<br>4. Read the new `accounts` row in a separate session. |
| Expected result | `/start` answers `302`; the parking row holds exactly `vk / cpc / spring2026 / banner_a / диплом`; after the callback the account's `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` hold those same five values; the parking row for that state value is gone. |
| Status | Not run |

### TC-14-INT-2.2 — Attribution parked on one instance is read back by another

| Field | Value |
|---|---|
| Description | `endpoints.md` calls parking the parameters on the handshake row «the most consequential call in this step». Every other scenario runs the start and the callback in one process, so an in-memory map keyed by handshake token passes all of them — including the no-leak-between-visitors case — while losing attribution on every real multi-instance sign-up. |
| Preconditions | Two application instances sharing one database and nothing else; `yandex-sub-6b90d1e5` has no account. |
| Test data | The five-value campaign set; `/start` served by instance A, `/callback` served by instance B, which never handled the start. |
| Steps | 1. Call `/start` with the five parameters against instance A; capture the state value.<br>2. Confirm instance B has no in-process knowledge of that state (restart or use a separate process).<br>3. Complete the callback for P2 against instance B.<br>4. Read the created `accounts` row in a separate session. |
| Expected result | The callback on instance B creates the account; its five `utm_*` columns hold `vk / cpc / spring2026 / banner_a / диплом` — none NULL; the values were read from the database row, not from any process state of instance A. |
| Status | Not run |

### TC-14-INT-2.3 — The campaign parameters are never handed to the provider

| Field | Value |
|---|---|
| Description | The parameters are our marketing metadata; forwarding them puts the campaign a visitor came from into a third party's request logs, and could collide with the provider's own query contract. |
| Preconditions | Provider configuration loaded; the `302` from `/start` captured rather than followed. |
| Test data | `/start` with the five-value campaign set. |
| Steps | 1. Call `GET /api/v1/auth/oauth/yandex/start` with the five `utm_*`.<br>2. Read the `Location` header of the `302` and parse its query string.<br>3. Read the `oauth_state_attribution` row for the minted state. |
| Expected result | The status is `302`; the `Location` query string contains none of `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` and none of the values `vk`, `cpc`, `spring2026`, `banner_a`, `диплом` under any parameter name; the five values are present in the parking row instead. |
| Status | Not run |

### TC-14-INT-2.4 — A first provider sign-in records both events; a later one records only the sign-in

| Field | Value |
|---|---|
| Description | A provider callback that creates an account is both a completed registration and a successful sign-in; recording only one of them makes the provider channel invisible in exactly one of Story 15's two funnels. |
| Preconditions | `yandex-sub-7f21c3a4` has no account; `analytics_events` empty for that visitor; the `Clock` is injected. |
| Test data | One callback creating the account, then a second callback for the same provider subject. |
| Steps | 1. Complete the callback for P1 for the first time.<br>2. Read the `analytics_events` rows written by that callback, with their `event_name` and `event_time`.<br>3. Complete a second callback for the same provider subject.<br>4. Read the rows written by the second callback. |
| Expected result | Step 2 yields exactly two rows — one `REGISTRATION_COMPLETED` and one `LOGIN_SUCCESS` — whose `event_time` values are byte-equal (one clock reading), and whose `sequence` values order them; step 4 yields exactly one row, `LOGIN_SUCCESS`, and no second `REGISTRATION_COMPLETED` exists for that account. |
| Status | Not run |

### TC-14-INT-2.5 — A callback arriving just inside the handshake's lifetime keeps the attribution

| Field | Value |
|---|---|
| Description | The handshake's expiry now gates business data, not just a security token. Only the past-expiry side was pinned; an expiry mis-sized, or evaluated against a different clock than the one that wrote the row, silently strips attribution from the whole provider channel. |
| Preconditions | `STATE_TTL_MINUTES = 10`; an injected `Clock` stub shared by the writer and the reader; the provider subject has no account. |
| Test data | `/start` with the five-value campaign set; clock advanced to `expires_at − 1 s`, and in a second run to `expires_at + 1 s` (`moment >= expires_at` is expired). |
| Steps | 1. Call `/start` with the five parameters and record `expires_at` on the handshake row.<br>2. Advance the injected clock to just before `expires_at`.<br>3. Complete the callback and read the created `accounts` row.<br>4. Repeat steps 1–3 with the clock advanced one tick past `expires_at` instead, and query `accounts` for that provider subject. |
| Expected result | In step 3 the account is created carrying all five values `vk / cpc / spring2026 / banner_a / диплом`, none NULL; in step 4 the callback is refused with the status it already returns for an expired state, no `accounts` row exists for that provider subject, and no `REGISTRATION_COMPLETED` or `LOGIN_SUCCESS` was recorded. |
| Status | Not run |

### TC-14-INT-2.6 — A provider-created account carries the same technical context as a registered one

| Field | Value |
|---|---|
| Description | The callback is itself a browser request, so the technical context is available there exactly as it is at registration. Only the campaign parameters need carrying through the handshake — without this scenario the whole provider channel registers with an empty context and nothing in the data reveals it. |
| Preconditions | Geolocation port answering `RU` for `203.0.113.44`; the provider subject has no account. |
| Test data | Callback arriving from `203.0.113.44` with a desktop `User-Agent` (Windows) and `Accept-Language: ru-RU,ru;q=0.9,en;q=0.8`. |
| Steps | 1. Begin the handshake with `/start`.<br>2. Complete the callback from `203.0.113.44` with that `User-Agent` and `Accept-Language`.<br>3. Read the created `accounts` row in a separate DB session. |
| Expected result | The row stores `registration_ip = 203.0.113.44`, `registration_country = RU`, a non-NULL `device_type` and `operating_system` drawn from the closed taxonomy (desktop / Windows, never a catch-all bucket), and `device_language = ru-ru` — the canonical lower-case BCP-47 tag of the highest-q entry; the same five columns are populated as for an account created through `POST /api/v1/auth/register` from the identical request. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the geolocation dependency resolves…` | `GeoLocationPort` fake returning a known country |
| `refuses the request` / `server error` / `unreadable` | Port fake raising the adapter's 4xx, 5xx and malformed-response failures |
| `received exactly one request per registration` | Call count on the port fake, asserted per registration |
| `does not answer` | Port fake hanging past the configured timeout |
| `nothing is committed after the caller has stopped waiting` | No `accounts` row after the client-side deadline aborts the request |
| `the deployment's proxy chain` | Multi-hop `X-Forwarded-For`; the trusted hop per the contract named in `endpoints.md` (`TRUSTED_PROXY_HOPS`) |
| `begins a provider sign-in carrying them` | `GET /api/v1/auth/oauth/{provider}/start` with the five `utm_*` query parameters |
| `a second instance that never handled the start` | A separate session/process sharing only the database — the start's process state gone |
| `the address the visitor is sent to` | The `Location` header of the 302 to the provider |
| `both carry the identical moment` | One `Clock` reading passed to both emissions; byte-equal `event_time` |
| `the clock advanced to just before the handshake expires` | Injected `Clock` stub at the `oauth_states` expiry boundary (`STATE_TTL_MINUTES = 10`) |
