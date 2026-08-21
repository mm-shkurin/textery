# Auto-generate: доклад — Security Tests

> **Provider and worker: read as GigaChat + `BackgroundTasks`, not OpenRouter + arq.**
> Written before 2026-07-09, when the engine was still planned as Claude via OpenRouter
> and the queue as `arq`. Neither shipped: generation goes through a direct `httpx`
> client to GigaChat (`backend/adapters/generation_provider/`), runs inline via
> FastAPI `BackgroundTasks`, and stale jobs are recovered by a periodic DB sweep —
> there is no worker process. `OPENROUTER_*` reads as the `GIGACHAT_*` credentials,
> "a stub OpenRouter server" as a stub GigaChat server. Behaviour is unchanged; the
> vendor and the transport are not. Source of truth: `ProductSpecification/technology.md`,
> `known-debt.md` #11 and #13. Verified against the code 2026-08-15.

Scope note: this story is fully anonymous (no auth, no JWT, no session/CSRF token yet —
see `known-debt.md` #2), so those categories are not applicable here. Generic 401/CORS/
security-header checks are handled globally, not per-story. Scenarios below target this
story's actual attack surface: free-text fields reaching storage and an LLM prompt, a
publicly-callable paid external API, and a by-id lookup with no owner concept.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.doklad@textery.test` / `Qa!Doklad2026` |
| Valid create body | `{"document_type": "доклад", "topic": "Влияние искусственного интеллекта на образование", "volume_pages": 5}` |
| Error body shape | `{"error_code": "<CODE>", "message": "<text>"}` |
| SQL payload | `'; DROP TABLE generations;--` |
| XSS payload | `<script>alert(1)</script>` and `<img src=x onerror=alert(1)>` |
| Credential sentinel | `GIGACHAT_CREDENTIALS = SENTINEL-Zx9Q-DO-NOT-LEAK` |
| Redaction marker | `[REDACTED]` |
| Length bounds | `requirements` ≤ 2000, `extra_wishes` ≤ 2000, `topic` ≤ 500 |
| Concurrency ceiling | the configured provider-call concurrency cap — record its value, e.g. `10` |

---

## 1. Injection Safety

### TC-01-SEC-1.1 — Injection payloads in free-text fields are stored and returned safely

| Field | Value |
|---|---|
| Description | Topic, requirements and extra wishes are attacker-controlled strings that reach a SQL statement and an LLM prompt. String-concatenated SQL anywhere on that path is a full-database compromise from an unauthenticated endpoint. |
| Preconditions | Account A signed in; the `generations` table exists and its row count is recorded. |
| Test data | `topic` = `'; DROP TABLE generations;--`, `requirements` = `<script>alert(1)</script>`, `extra_wishes` = `" OR 1=1 --` |
| Steps | 1. `POST /api/v1/generations` with the three payloads above.<br>2. `GET /api/v1/generations/{generation_id}`.<br>3. Verify the `generations` table still exists and count its rows.<br>4. Read the server log for the request. |
| Expected result | `201 Created`; step 2 returns the three payload strings back verbatim as JSON string values; the table still exists and holds exactly one more row than before; no database error, no syntax error and no `relation does not exist` appears in the log or in any response body. |
| Status | Not run |

---

## 2. Output Encoding (XSS)

### TC-01-SEC-2.1 — Document content and echoed input are served as escaped text

| Field | Value |
|---|---|
| Description | The generated document is produced by a third party and rendered in the user's browser; markup that survives into an HTML context is stored XSS with an LLM as the injection vector. |
| Preconditions | A generation whose stub provider response contains HTML markup has completed; account A signed in. |
| Test data | Stub provider content `<img src=x onerror=alert(1)>Доклад`; `topic` also set to `<script>alert(1)</script>` |
| Steps | 1. Run the generation to `completed` with the stub content above.<br>2. `GET /api/v1/generations/{generation_id}` and read the raw response.<br>3. Open the completed generation in the browser and inspect the rendered DOM. |
| Expected result | The response `Content-Type` is `application/json`; `content` and `topic` are JSON string values with the markup intact as data (`<` is not interpreted server-side); in the browser the markup appears as literal visible text, no `<script>` or `<img>` element is created in the DOM, and no `alert` fires. |
| Status | Not run |

---

## 3. Mass Assignment

### TC-01-SEC-3.1 — Server-owned fields cannot be set by the client

| Field | Value |
|---|---|
| Description | `status`, `id` and `created_at` are the server's; a body that could set them would let a caller mint a completed generation, collide with an existing id, or pin a row at the top of the feed. |
| Preconditions | Account A signed in. |
| Test data | Valid body plus `"status": "completed"`, `"id": "00000000-0000-4000-8000-000000000000"`, `"created_at": "2000-01-01T00:00:00Z"`; separately, `"document_type": "диссертация"` |
| Steps | 1. `POST /api/v1/generations` with the four extra fields in the body.<br>2. Read the response and then `GET /api/v1/generations/{generation_id}`.<br>3. Repeat the post with only `document_type: "диссертация"` added to an otherwise valid body. |
| Expected result | Steps 1–2: `status` is `"pending"`, `generation_id` is a fresh server UUID (not `0000…0000`), `created_at` is server time within seconds of the call — none of the three supplied values is persisted. Step 3: `422` with `{"error_code": "INVALID_DOCUMENT_TYPE", "message": "document_type must be one of: доклад, эссе, сочинение, реферат"}` and no row created. |
| Status | Not run |

---

## 4. Input Length Limits

### TC-01-SEC-4.1 — Oversized free-text fields are rejected before reaching the generation provider

| Field | Value |
|---|---|
| Description | The provider is paid per token. A field with no ceiling lets an unauthenticated caller set the bill from the request body — the cheapest denial-of-wallet there is. |
| Preconditions | Account A signed in; stub GigaChat server call counter reset to 0. |
| Test data | `requirements` of 2001 characters, then `extra_wishes` of 2001 characters (limit 2000 each) |
| Steps | 1. Reset the stub's call counter.<br>2. `POST /api/v1/generations` with the 2001-character `requirements`.<br>3. `POST /api/v1/generations` with the 2001-character `extra_wishes`.<br>4. Read the stub's call count. |
| Expected result | Both posts answer `400` with `{"error_code": "VALIDATION_ERROR", "message": "requirements must be at most 2000 characters"}` / `"extra_wishes must be at most 2000 characters"`; the stub's call count is still `0` — the refusal happens before any provider call and before any row is written. |
| Status | Not run |

---

## 5. Non-Enumerable Resource Identifiers

### TC-01-SEC-5.1 — Generation identifiers are not predictable across consecutive creations

| Field | Value |
|---|---|
| Description | The id is the only thing standing between a caller and someone else's generation on a by-id read. A sequential integer makes the whole table walkable with a for-loop. |
| Preconditions | Account A signed in. |
| Test data | Ten generations created back to back from the valid body |
| Steps | 1. `POST /api/v1/generations` ten times in succession.<br>2. Collect the ten `generation_id` values.<br>3. Compare each with its predecessor. |
| Expected result | Every id is a 36-character UUID (version 4 — the 13th hex digit is `4`); no id is an integer or contains a sequence counter; no id can be derived from its predecessor by increment, and the ten values share no ordered prefix. |
| Status | Not run |

---

## 6. Secret & Internal-Detail Disclosure

### TC-01-SEC-6.1 — A generation-provider failure never leaks credentials or raw upstream detail

| Field | Value |
|---|---|
| Description | The failure path is where secrets escape: an exception repr that carries the outbound request, or an upstream error body echoed into `error_message`, hands the credential to any caller who can make the provider fail. |
| Preconditions | Backend started with `GIGACHAT_CREDENTIALS = SENTINEL-Zx9Q-DO-NOT-LEAK`; stub GigaChat server returns `401` with a body echoing the credential; server log capture enabled. |
| Test data | Sentinel `SENTINEL-Zx9Q-DO-NOT-LEAK`; stub error body `{"error": "invalid token SENTINEL-Zx9Q-DO-NOT-LEAK for host gigachat.internal"}`; redaction marker `[REDACTED]` |
| Steps | 1. Run a generation to failure against that stub.<br>2. `GET /api/v1/generations/{generation_id}` and search the whole response for the sentinel.<br>3. Search the captured server log for the sentinel and for the marker. |
| Expected result | Response `status` is `"failed"` with `error_message` = `Не удалось сгенерировать документ. Попробуйте позже.`; the string `SENTINEL-Zx9Q-DO-NOT-LEAK` appears nowhere in the response, nor does the stub's raw error body or the upstream host name; the captured log contains `[REDACTED]` in place of the credential and does not contain the raw sentinel anywhere. |
| Status | Not run |

---

## 7. Resource Exhaustion / Cost-Amplification Guard

### TC-01-SEC-7.1 — A flood of submissions cannot drive unbounded concurrent provider calls

| Field | Value |
|---|---|
| Description | Every accepted submission spends money at a third party. Without a hard concurrency cap, one scripted flood converts directly into an uncapped bill and a rate-limit ban. |
| Preconditions | Backend running with the concurrency ceiling at its configured value; stub GigaChat server counts concurrent in-flight calls and holds each for 5 s. |
| Test data | 500 submissions in 10 seconds against a ceiling of `10`; sampling every 200 ms |
| Steps | 1. Record the configured concurrency ceiling.<br>2. Submit 500 valid generation requests within 10 seconds.<br>3. Sample the stub's concurrent in-flight count every 200 ms until the backlog drains.<br>4. Read the peak sample. |
| Expected result | The peak concurrent provider-call count never exceeds the configured ceiling at any sample; the excess submissions wait rather than issuing calls; the ceiling holds for the whole drain, not just at the start of the burst. |
| Status | Not run |

---

## 8. Header Injection

### TC-01-SEC-8.1 — A malformed idempotency key is rejected, not passed through

| Field | Value |
|---|---|
| Description | The idempotency key is a client string that becomes a stored value and a log field. CR/LF in it is log forging upstream and header injection anywhere it is echoed. |
| Preconditions | Account A signed in; server log capture enabled; no generation exists for account A. |
| Test data | `Idempotency-Key: key-1\r\nX-Injected: 1` (literal CR and LF), and a key of 200 characters (bound is 128) |
| Steps | 1. `POST /api/v1/generations` with the CR/LF key above.<br>2. Inspect the raw response headers.<br>3. `POST /api/v1/generations` with the 200-character key.<br>4. Read the captured log lines and `GET /api/v1/generations`. |
| Expected result | Both requests are refused in this API's envelope — `400` with `{"error_code": "MISSING_IDEMPOTENCY_KEY" \| "INVALID_IDEMPOTENCY_KEY", "message": "<text>"}` — never `201`; no `X-Injected` header is present in the response and the response has exactly one header block; no raw CR or LF reaches storage or appears as a line break in the captured log; `GET /api/v1/generations` shows no row was created. |
| Status | Not run |

---

## 9. Oversized Payload Rejection

### TC-01-SEC-9.1 — A request with deeply nested or oversized JSON is rejected before parsing cost balloons

| Field | Value |
|---|---|
| Description | This endpoint is publicly reachable and unthrottled; a body that is expensive merely to parse turns a single request into a CPU denial of service before any business rule has a chance to refuse it. |
| Preconditions | Backend running; stub GigaChat server call counter reset to 0; process CPU and memory sampled during the call. |
| Test data | A 50 MB JSON body, and a body nesting 10 000 levels of `{"a":` — both sent to `POST /api/v1/generations` |
| Steps | 1. Send the 50 MB body and measure the time to the response.<br>2. Send the 10 000-level nested body.<br>3. Read the stub's call count and sample the process's CPU/memory during both.<br>4. `GET /api/v1/generations`. |
| Expected result | Both requests are refused with a `4xx` (a body-size or malformed-body refusal), never a `201` and never a hang; the refusal arrives before any validation of `topic`/`volume_pages` runs; the stub's call count is `0`; the process does not restart and its memory returns to baseline; step 4 shows no row was created. |
| Status | Not run |
