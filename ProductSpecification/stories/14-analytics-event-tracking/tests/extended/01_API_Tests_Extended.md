> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — API Tests (Extended)

> **UNBLOCKED 2026-08-19.** §1.1 and §3.1 deferred to «the representation / the outcome the
> contract names» and no contract named one. `endpoints.md` § "The five decisions the test spec
> was blocked on" now records both, and both scenarios below assert the literal outcome.

Shared test data is inherited from `01_API_Tests.md` (the ingest route
`POST /api/v1/analytics/events` with its `event_name` / `visitor_id` / `occurrence_key` /
`payload` / `degraded` body, the canonical error envelope `{"error_code","message"}`, the
extended routes `POST /api/v1/auth/register` and `GET /api/v1/auth/oauth/{provider}/start`,
the 200-code-point `utm_*` bound, and the rule that every persistence assertion is re-read in
a **fresh session**). Cases that need their own values name them below.

---

## 1. Field Shapes at the Edges

### TC-14-API-EXT-1.1 — An omitted, null and empty payload are three inputs with one stored value

| Field | Value |
|---|---|
| Description | `analytics_events.payload` is `NOT NULL` with server default `{}`. If any of the three inputs stored NULL or was refused, Story 15 would carry two spellings of "no context" at every read, forever. |
| Preconditions | No session (no `Authorization` header). Database reachable. |
| Test data | One `visitor_id` (v4 UUID), three distinct `occurrence_key` v4 UUIDs, `event_name` = `SITE_VISITED`. Request A omits `payload` entirely; request B sends `"payload": null`; request C sends `"payload": {}`. |
| Steps | 1. `POST /api/v1/analytics/events` with body A (no `payload` key).<br>2. `POST /api/v1/analytics/events` with body B (`"payload": null`).<br>3. `POST /api/v1/analytics/events` with body C (`"payload": {}`).<br>4. In a fresh session, read the three `analytics_events` rows by their `occurrence_key`. |
| Expected result | All three answer `204 No Content` with an empty body. Three rows exist. Each row's `payload` column equals `{}` (an empty JSONB object) and is not NULL; the column is `NOT NULL`, so no input produced an absent value. |
| Status | Not run |

### TC-14-API-EXT-1.2 — An empty attribution value is stored as absent, not as an empty value

| Field | Value |
|---|---|
| Description | A link ending `?utm_term=` carries no term. Storing `''` would make Story 15 read an empty string as a campaign term that no marketing link ever produced. |
| Preconditions | `qa.utmempty@textery.test` not registered. |
| Test data | `POST /api/v1/auth/register` body with valid credentials plus `utm_source: "vk"`, `utm_medium: "cpc"`, `utm_campaign: "spring2026"`, `utm_content: "banner"`, `utm_term: ""` (present, empty). |
| Steps | 1. `POST /api/v1/auth/register` with the body above.<br>2. In a fresh session, read the created row in `accounts` and its five `utm_*` columns. |
| Expected result | Registration answers exactly the status and body it answers with the `utm_*` omitted (no new `error_code`). `accounts.utm_term` is NULL — never `''`. The other four store `vk` / `cpc` / `spring2026` / `banner`: an empty member is *absent*, not *unusable*, so the set is kept. |
| Status | Not run |

### TC-14-API-EXT-1.3 — A partial attribution set is frozen as a set, not merged later

| Field | Value |
|---|---|
| Description | First touch means one set. If a later, fuller link merged its members into the frozen set, the account would carry an attribution combination that no single marketing link ever produced. |
| Preconditions | `qa.firsttouch@textery.test` not registered. Browser store empty before step 1. |
| Test data | First visit: `<app_url>/?utm_source=vk` only. Later visit: `<app_url>/?utm_source=email&utm_medium=cpc&utm_campaign=newsletter_may&utm_content=hero&utm_term=диплом`. |
| Steps | 1. Open the first link with an empty store, so `utm_source=vk` alone becomes the frozen first touch.<br>2. Open the later, full link in the same browser.<br>3. Register `qa.firsttouch@textery.test` and record the `POST /api/v1/auth/register` body actually sent.<br>4. In a fresh session, read the account's five `utm_*` columns. |
| Expected result | Registration succeeds unchanged. `accounts.utm_source` = `vk` — the first visit's value. `utm_medium`, `utm_campaign`, `utm_content`, `utm_term` are all NULL; no member of the second link appears in any column, and `utm_source` was not overwritten with `email`. |
| Status | Not run |

### TC-14-API-EXT-1.3a — An absent member keeps the set; an unusable member discards it

| Field | Value |
|---|---|
| Description | The two halves are one line apart in the implementation and opposite in outcome: absent members are legitimate (`None`), an over-bound member is `_Unusable` and discards all five (`domain/src/analytics/attribution.py`). |
| Preconditions | `qa.utmpartial@textery.test` and `qa.utmoverbound@textery.test` both unregistered. |
| Test data | Registration P: `utm_source: "vk"`, `utm_campaign: "spring2026"`, the other three omitted. Registration Q: `utm_source: "vk"`, `utm_medium: "cpc"`, `utm_content: "banner"`, `utm_term: "диплом"` all valid, plus `utm_campaign` = the letter `a` repeated 201 times (one code point over the 200 bound). |
| Steps | 1. `POST /api/v1/auth/register` as registration P.<br>2. In a fresh session read P's account's five `utm_*` columns.<br>3. `POST /api/v1/auth/register` as registration Q.<br>4. In a fresh session read Q's account's five `utm_*` columns.<br>5. Compare the two responses' status codes and body shapes with each other and with an identical registration carrying no `utm_*` at all. |
| Expected result | P stores `utm_source` = `vk` and `utm_campaign` = `spring2026`; the other three read NULL — an absent member does not discard the set. Q stores NULL in **all five** columns, including the four valid ones; no 201-character or 200-character truncated value is stored anywhere. Both registrations answer identically to each other and to the no-`utm_*` registration: same status code, same body shape, same `error_code` set (none). |
| Status | Not run |

The two halves are one line apart in the implementation and opposite in outcome. An
implementation that discards the set whenever any member is missing loses attribution for every
link that carries only `utm_source`; one that drops only the offending member writes sets no
marketing link ever produced.

### TC-14-API-EXT-1.4 — Attribution text outside the basic plane survives the round trip

| Field | Value |
|---|---|
| Description | The `utm_*` bound is counted in **code points after NFC**, not bytes; an astral-plane character is 1 code point and 4 UTF-8 bytes, so a byte-counting bound or a lossy encoding step corrupts or discards a legal value. |
| Preconditions | `qa.utmastral@textery.test` not registered; the `accounts` `utm_*` columns are `text` on a UTF-8 database. |
| Test data | `utm_campaign` = `Кампания 🎓𝔘𝔫𝔦` — Cyrillic plus astral-plane code points (emoji U+1F393 and mathematical letters), well under 200 code points; the other four omitted. |
| Steps | 1. `POST /api/v1/auth/register` carrying that `utm_campaign`.<br>2. In a fresh session (never the writing session), read `accounts.utm_campaign`. |
| Expected result | Registration succeeds unchanged. The fresh read returns the value byte-for-byte identical to what was sent, in NFC — no replacement character `�`, no truncation at the astral boundary, no surrogate escape. The other four `utm_*` read NULL, and the value was not discarded as unusable. |
| Status | Not run |

---

## 2. Language and Device Derivation

### TC-14-API-EXT-2.1 — The highest-priority language tag wins, and it is stored canonically

| Field | Value |
|---|---|
| Description | `Accept-Language` states priority with `q`, not with order. Taking the first listed entry stores the wrong language whenever a client lists a lower-`q` tag first. |
| Preconditions | `qa.lang1@textery.test` not registered. |
| Test data | Header `Accept-Language: ru;q=0.9,en-US;q=1.0` on `POST /api/v1/auth/register`. |
| Steps | 1. `POST /api/v1/auth/register` with that `Accept-Language` header.<br>2. In a fresh session, read `accounts.device_language`. |
| Expected result | `accounts.device_language` = `en-us` — the highest-`q` entry (`en-US`, q=1.0), not the first-listed `ru`; stored lower-cased in canonical BCP-47 form, so neither `en-US` nor `ru` appears in the column. |
| Status | Not run |

### TC-14-API-EXT-2.2 — The same language written three ways is stored one way

| Field | Value |
|---|---|
| Description | Canonicalization must be locale-invariant. Three casings that reach three different stored values split one language into three populations in every Story 15 report. |
| Preconditions | `qa.lang.a@textery.test`, `qa.lang.b@textery.test`, `qa.lang.c@textery.test` all unregistered. |
| Test data | Three registrations sending `Accept-Language: ru-RU`, `Accept-Language: RU-ru`, and `Accept-Language: rU-Ru` respectively. |
| Steps | 1. Register account A with `Accept-Language: ru-RU`.<br>2. Register account B with `Accept-Language: RU-ru`.<br>3. Register account C with `Accept-Language: rU-Ru`.<br>4. In a fresh session, read `accounts.device_language` for all three. |
| Expected result | All three columns hold the identical string `ru-ru`; a `SELECT DISTINCT device_language` over the three rows returns exactly one value. No row keeps the letter case it was sent in. |
| Status | Not run |

### TC-14-API-EXT-2.3 — An unrecognised browser is stored as unknown, never as a default

| Field | Value |
|---|---|
| Description | The device taxonomy is closed (`domain/src/analytics/device.py`); an unrecognised agent maps to `None`, never to a bucket. Defaulting to `DESKTOP` inflates the most common device type with every crawler and every broken parse, invisibly. |
| Preconditions | `qa.ua.unknown@textery.test` and `qa.ua.absent@textery.test` unregistered. |
| Test data | Registration U with `User-Agent: qa-unrecognised-agent/1.0` (naming no platform this taxonomy knows). Registration V with the `User-Agent` header entirely absent. |
| Steps | 1. `POST /api/v1/auth/register` as U with the unrecognised agent.<br>2. `POST /api/v1/auth/register` as V with no `User-Agent` header at all.<br>3. In a fresh session, read `accounts.device_type` and `accounts.operating_system` for both. |
| Expected result | Both registrations succeed unchanged. For both accounts `device_type` is NULL and `operating_system` is NULL. Neither column holds `DESKTOP`, `MOBILE`, `TABLET`, any of `ANDROID`/`IOS`/`WINDOWS`/`MACOS`/`LINUX`, nor a catch-all such as `OTHER` or `UNKNOWN`. |
| Status | Not run |

---

## 3. Occurrence Keys

### TC-14-API-EXT-3.1 — One occurrence key cannot be reused for a different event

| Field | Value |
|---|---|
| Description | The same key under the same name is the React StrictMode replay and must collapse to `204`. The same key under a *different* name is not a replay of anything — collapsing it would answer success while silently discarding a real event. |
| Preconditions | No session. One visitor identity, no events stored for it. |
| Test data | `visitor_id` V (v4 UUID), `occurrence_key` K (v4 UUID). Request 1: `event_name` = `SITE_VISITED`. Request 2: `event_name` = `EDITOR_OPENED`, same V and K. Request 3: `event_name` = `SITE_VISITED`, same V and K. |
| Steps | 1. `POST /api/v1/analytics/events` with V, K, `SITE_VISITED`; record the stored row (its `id`, `event_name`, `payload`, `event_time`).<br>2. `POST /api/v1/analytics/events` with V, K, `EDITOR_OPENED`.<br>3. In a fresh session, count rows for (V, K) and re-read the row from step 1.<br>4. `POST /api/v1/analytics/events` with V, K, `SITE_VISITED` again.<br>5. In a fresh session, count rows for (V, K) again. |
| Expected result | Step 1 answers `204`. Step 2 answers `409` with the canonical envelope `{"error_code":"OCCURRENCE_KEY_CONFLICT","message":…}`, and the message echoes no part of the request. After step 3 exactly one row exists for (V, K), its `event_name` is still `SITE_VISITED`, and its `id`, `payload` and `event_time` are unchanged — no `EDITOR_OPENED` row was written. Step 4 answers `204` (a replay, not a conflict) and step 5 still counts exactly one row. |
| Status | Not run |

The last two lines are what separates the conflict from the replay: collapsing a different
event name under a stored key would answer success while silently discarding a real event.

### TC-14-API-EXT-3.2 — Two visitors reporting the same occurrence key are two events

| Field | Value |
|---|---|
| Description | The uniqueness constraint is `(visitor_id, occurrence_key)`, partial over client-origin rows. A key scoped globally instead would let one browser's key silence another's event — and would make the key a probe into other visitors' history. |
| Preconditions | No session. No events stored for either visitor. |
| Test data | Two distinct `visitor_id` values V1 and V2 (v4 UUIDs), one shared `occurrence_key` K, `event_name` = `SITE_VISITED` for both. |
| Steps | 1. `POST /api/v1/analytics/events` with V1, K, `SITE_VISITED`.<br>2. `POST /api/v1/analytics/events` with V2, K, `SITE_VISITED`.<br>3. In a fresh session, read all `analytics_events` rows whose `occurrence_key` = K. |
| Expected result | Both requests answer `204` and the two responses are byte-identical. Exactly two rows exist for K — one with `visitor_id` = V1 and one with `visitor_id` = V2, with distinct `id` and distinct `sequence`. Neither request answers `409`. |
| Status | Not run |

---

## 4. Ordering Under Load

### TC-14-API-EXT-4.1 — Many events for one visitor keep a strict, gap-free order

| Field | Value |
|---|---|
| Description | `sequence` is a `BigInteger` `Identity(always=True)` column and the only total-order key — `event_time` collides by design. Two rows sharing a position, or an order that differs between reads, makes every Story 15 funnel non-deterministic. |
| Preconditions | No session. No events stored for the visitor. Several connections/processes available, sharing only the database. |
| Test data | One `visitor_id` V; 100 events reported in quick succession from at least 4 concurrent connections, each with its own `occurrence_key` (100 distinct v4 UUIDs), mixed across the three accepted names. |
| Steps | 1. Report the 100 events for V concurrently across the connections.<br>2. In a fresh session, read all rows for V ordered by `sequence`.<br>3. Repeat the identical ordered read twice more. |
| Expected result | 100 rows are stored. The 100 `sequence` values are pairwise distinct — no two rows share a position. All three ordered reads return the identical sequence of `id` values in the identical order. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the stored payload is the empty object` | `payload = {}` in a `NOT NULL` column defaulting to `{}` — the decision recorded in `endpoints.md` |
| `refused as a conflicting occurrence` | `409 OCCURRENCE_KEY_CONFLICT`, canonical envelope |
| `characters outside the basic plane` | Astral-plane code points — the fixture that separates byte and code-point bounds |
| `several language tags with differing priorities` | `Accept-Language: ru;q=0.9,en-US;q=1.0` |
| `no two share a position` | Distinct `sequence` values |
