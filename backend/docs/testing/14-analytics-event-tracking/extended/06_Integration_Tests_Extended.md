<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — Integration Tests (Extended)

> **UNBLOCKED 2026-08-19.** The contradiction is resolved in the only direction that keeps an
> existing route's behaviour: the handshake **proceeds with the attribution dropped**. See
> `endpoints.md` § "Attribution is fail-open on both auth routes".

Shared test data is inherited from `06_Integration_Tests.md`: the `Geolocation` port fake with
its resolve / refuse / server-error / unreadable / hang modes and its per-registration call
counter, `GEOLOCATION_TIMEOUT_SECONDS` (default `1.5`), the five `utm_*` parameters on
`GET /api/v1/auth/oauth/{provider}/start`, the `oauth_states` handshake row with its expiry and
the `oauth_state_attribution` row keyed on `state_value`, the provider fake returning to
`/callback`, and the injected `Clock`.

---

## 1. Geolocation Responses at the Edges

### TC-14-INT-EXT-1.1 — A country the taxonomy does not recognise is stored as unset, not guessed

| Field | Value |
|---|---|
| Description | The adapter upper-cases whatever string the dependency returns. A provider answering a non-country code, a region name or a sentinel would write that value into `registration_country` as if it were a country, and Story 15 would group by it forever with nothing revealing that the value is not real. |
| Preconditions | Geolocation configured and healthy; `qa.geo1@textery.test` not registered. Registration recorded with its structured log. |
| Test data | The dependency answers `{"countryCode": "ZZ"}` — a value outside the recognised country taxonomy (**placeholder:** no taxonomy or ISO-3166-1 alpha-2 check exists in `backend/adapters/geolocation_provider/src/geolocation/http_geolocation.py` today; the recognised set has to be named before this case can assert against it). Credentials `qa.geo1@textery.test` / `Qa!Geo2026`. |
| Steps | 1. Arm the dependency to answer `ZZ`.<br>2. `POST /api/v1/auth/register` with the credentials above.<br>3. Read the response status and body.<br>4. `SELECT registration_country FROM accounts WHERE email = 'qa.geo1@textery.test'`.<br>5. Read the structured log records emitted during the registration. |
| Expected result | Registration answers its normal success status and body, with no new `error_code`; `registration_country` reads as SQL NULL — not `'ZZ'`, not `'zz'`, not a nearest guess; exactly one structured log record names the unrecognised answer, carrying the rejected code as a field and no credential or token; the other four technical-context columns are written as usual. |
| Status | Not run |

### TC-14-INT-EXT-1.2 — An answer that arrives just inside the deadline is used

| Field | Value |
|---|---|
| Description | A margin mis-sized on the client side — a connect timeout instead of a total one, or a deadline shorter than the configured value — silently throws away every slow-but-valid answer, and the whole country column degrades to NULL with nothing going red. |
| Preconditions | Geolocation configured with `GEOLOCATION_TIMEOUT_SECONDS=1.5`; `qa.geo2@textery.test` not registered; the same account's registration timed once with an instant lookup as the budget baseline. |
| Test data | The dependency answers `{"countryCode": "RU"}` after `1.4 s` — inside the 1.5 s deadline by a 0.1 s margin; credentials `qa.geo2@textery.test` / `Qa!Geo2026`. |
| Steps | 1. Time a registration with an instant lookup; record it as the baseline.<br>2. Arm the dependency to answer `RU` at 1.4 s.<br>3. `POST /api/v1/auth/register` and time it end to end.<br>4. Read the response status and body.<br>5. `SELECT registration_country FROM accounts WHERE email = 'qa.geo2@textery.test'`. |
| Expected result | Registration answers its normal success status; `registration_country` reads exactly `'RU'` — the slow answer is used, not abandoned; the request completes in under `baseline + 1.5 s` (the configured timeout is the whole allowance the lookup may add) and the dependency was asked exactly once. |
| Status | Not run |

### TC-14-INT-EXT-1.3 — A dependency that is slow does not compound across concurrent registrations

| Field | Value |
|---|---|
| Description | One shared `AsyncClient` with a bounded connection pool, or a lookup awaited under a lock, turns N slow registrations into N sequential deadlines — under the throughput profile that is the registration path serializing on a marketing column. |
| Preconditions | Geolocation configured with `GEOLOCATION_TIMEOUT_SECONDS=1.5`; ten unregistered addresses `qa.geo3-01@textery.test` … `qa.geo3-10@textery.test`. |
| Test data | The dependency answers `{"countryCode": "RU"}` after `1.2 s` for every call; 10 registrations issued concurrently; the single-registration baseline from TC-14-INT-EXT-1.2 step 1. |
| Steps | 1. Arm the dependency to answer at 1.2 s for every call.<br>2. Issue the 10 registrations concurrently and time each one individually and the batch as a whole.<br>3. Read every response status.<br>4. `SELECT email, registration_country FROM accounts` for the ten addresses.<br>5. Read the dependency's call count and the overlap of its in-flight calls. |
| Expected result | All 10 answer their normal success status; each individual registration completes in under `baseline + 1.5 s`, i.e. none paid another's 1.2 s; the whole batch completes in well under `10 × 1.2 s` — the lookups overlapped rather than queued; all ten accounts store `'RU'`; the dependency recorded exactly 10 calls, with more than one in flight at the same moment. |
| Status | Not run |

---

## 2. OAuth Handshake Edges

### TC-14-INT-EXT-2.1 — Attribution parked against a handshake does not leak between visitors

| Field | Value |
|---|---|
| Description | The parked parameters are keyed on the handshake's `state_value`. Anything keyed more loosely — a process-wide "last start" or a per-provider slot — hands the second visitor's campaign to the first account, and both rows look perfectly plausible afterwards. |
| Preconditions | `oauth_state_attribution` and `oauth_states` empty; the provider fake able to return two distinct callbacks; neither `qa.oauth-a@textery.test` nor `qa.oauth-b@textery.test` registered. |
| Test data | Visitor A: `?utm_source=vk&utm_campaign=spring2026&utm_medium=cpc&utm_content=a1&utm_term=t1`. Visitor B: `?utm_source=email&utm_campaign=newsletter_may&utm_medium=mail&utm_content=b1&utm_term=t2`. Both interleaved on the same provider. |
| Steps | 1. `GET /api/v1/auth/oauth/yandex/start` with visitor A's five parameters; capture `state` from the `Location` header.<br>2. `GET .../start` with visitor B's five parameters; capture its `state`.<br>3. Read both `oauth_state_attribution` rows.<br>4. Complete B's callback, then A's callback.<br>5. Read the five `utm_*` on each created account. |
| Expected result | Two `oauth_state_attribution` rows exist with distinct `state_value`, each holding exactly its own visitor's five values; the account created from B's callback carries `utm_source='email'`, `utm_campaign='newsletter_may'`, `utm_medium='mail'`, `utm_content='b1'`, `utm_term='t2'`; the account from A's callback carries `vk` / `spring2026` / `cpc` / `a1` / `t1`; no value from one visitor appears on the other's account, and neither set is mixed. |
| Status | Not run |

### TC-14-INT-EXT-2.2 — A handshake that is never completed leaves nothing behind

| Field | Value |
|---|---|
| Description | `oauth_state_attribution` carries no foreign key to `oauth_states` by design, so nothing removes its rows automatically. An abandoned handshake that keeps its parked row forever is an analytics table that grows with every bot that touches `/start`. |
| Preconditions | Both tables empty; the injected `Clock` able to advance past the handshake expiry; no callback is ever issued for this state. |
| Test data | `GET /api/v1/auth/oauth/yandex/start?utm_source=vk&utm_campaign=spring2026&utm_medium=cpc&utm_content=c1&utm_term=t3`; the clock advanced one tick past the `oauth_states` expiry. |
| Steps | 1. Begin the handshake and capture `state` from the `Location` header.<br>2. Confirm one `oauth_state_attribution` row exists for that `state_value`.<br>3. Advance the clock one tick past the handshake's expiry; never issue a callback.<br>4. Let the handshake-cleanup path run.<br>5. `SELECT count(*) FROM accounts`, `SELECT count(*) FROM oauth_states`, `SELECT count(*) FROM oauth_state_attribution WHERE state_value = <state>`. |
| Expected result | No `accounts` row is created; the expired `oauth_states` row is gone; the `oauth_state_attribution` row for that `state_value` is gone too — the parked parameters do not outlive the handshake they were parked against; a callback presented for that `state` afterwards is refused and still creates no account. |
| Status | Not run |

### TC-14-INT-EXT-2.3 — A provider sign-in with no campaign parameters creates an account with none

| Field | Value |
|---|---|
| Description | The ordinary provider sign-up — no marketing link anywhere. A read of the parked row that assumes it exists, or a default set written when none was carried, turns "arrived directly" into a fabricated campaign for the whole organic channel. |
| Preconditions | Both tables empty; `qa.oauth-c@textery.test` has no account; the provider fake returns that identity. |
| Test data | `GET /api/v1/auth/oauth/yandex/start` with **no** `utm_*` query parameters, followed by its callback. |
| Steps | 1. `GET /api/v1/auth/oauth/yandex/start` with no `utm_*`; read the status and `Location`.<br>2. Read `oauth_state_attribution` for that `state_value`.<br>3. Complete the callback.<br>4. Read the created account's five `utm_*` columns.<br>5. Read the account's five technical-context columns. |
| Expected result | `/start` answers `302` with a `Location` to the provider; the callback creates exactly one account; all five `utm_*` read as SQL NULL — no `''`, no default campaign, no row inherited from another handshake; the technical context (ip, country, device type, OS, language) is still recorded from the callback request, so "no campaign" does not mean "no context". |
| Status | Not run |

### TC-14-INT-EXT-2.4 — Campaign parameters over the bound do not break the handshake

| Field | Value |
|---|---|
| Description | `/start` answers `302 / 404 / 500` today and has no `400` at all; this story does not give it one. An over-bound parameter must be dropped whole (all five, never one member), the visitor redirected exactly as with no parameters, and no truncated value stored — a truncated campaign is a campaign that never existed. |
| Preconditions | Both tables empty; the same request issued once *without* the `utm_*` recorded as the comparison baseline (status, `Location` host, path and query); `qa.oauth-d@textery.test` has no account. |
| Test data | `utm_campaign` = 400 × `"a"` (far over the 200-code-point bound after NFC), with four usable members alongside: `utm_source=vk`, `utm_medium=cpc`, `utm_content=d1`, `utm_term=t4`. |
| Steps | 1. `GET /api/v1/auth/oauth/yandex/start` with **no** `utm_*`; record status, `Location` host, path and query keys as the baseline.<br>2. `GET .../start` with the four usable members plus the 400-character `utm_campaign`.<br>3. Compare status and `Location` host/path/query against the baseline.<br>4. Read `oauth_state_attribution` for that `state_value`.<br>5. Complete the callback and read the created account's five `utm_*`.<br>6. Search `oauth_state_attribution` and `accounts` for any value of length 200 or any prefix of the 400-character string. |
| Expected result | Step 2 answers `302` — the same status and the same `Location` host, path and query as the baseline request, byte for byte; no `400` is answered by this route under any input in this case; the callback creates exactly one account; all five `utm_*` on it read as SQL NULL, including the four members that were individually usable (the set is discarded whole, per `endpoints.md`); no 200-character truncation and no prefix of the 400-character value exists in `oauth_state_attribution` or `accounts`; exactly one structured log record names `utm_campaign` as the field that failed the bound, carrying no value. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a code outside the expected set` | A value the country taxonomy does not contain |
| `just before its deadline` | Fake port answering at the configured timeout minus a margin |
| `parked against a handshake` | The `utm_*` stored on the `oauth_states` row |
| `the handshake expires without a callback` | `oauth_states` row past its expiry, never consumed |
| `redirected exactly as with no campaign parameters` | Same `302` and same `Location` host/path/query as the identical request without the `utm_*` — asserted against that request |
| `answers no status code it does not answer without them` | `302 / 404 / 500` only; a `400` from this route fails the scenario |
