# OAuth sign-in — Security Tests

Story-specific attack surface only. Generic 401/headers/CORS/HTTPS are tested globally.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Provider identity P1 | provider `yandex`, subject `1000000000000123`, email `qa.oauth@textery.test` |
| Valid handoff code | `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847` |
| Frontend callback | `/auth/callback?code=<opaque>&provider=yandex` or `?error=oauth_failed&provider=yandex` |
| Exchange refusal | `400`, `{"error_code": "INVALID_OR_EXPIRED_OAUTH_CODE", "message": "<generic text>"}` |
| Rate limit | `OAUTH_RATE_LIMIT_MAX_REQUESTS=40` per `OAUTH_RATE_LIMIT_WINDOW_SECONDS=60`, per (leg, source); refusal `429` / `OAUTH_RATE_LIMITED` |
| Generic 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |

---

## 1. Open redirect

### TC-16-SEC-1.1 — A crafted callback redirect target cannot drive an external redirect

| Field | Value |
|---|---|
| Description | A sign-in that will forward the browser wherever a crafted link says is a phishing hop signed with our own domain's credibility. |
| Preconditions | A signed-out visitor; the exchange resolves a valid session. |
| Test data | Crafted targets `https://evil.test/steal`, `//evil.test`, `/\evil.test`, `/\/evil.test`, `//\evil.test` |
| Steps | 1. Open the callback with the valid code and each crafted target in turn (router state / callback param).<br>2. Let the sign-in complete.<br>3. Read the resulting document URL. |
| Expected result | Every run lands on the in-app default `/`; the document origin stays the app's own; there is no request to `evil.test` in the network log for any variant, including the backslash-normalized forms. |
| Status | Not run |

---

## 2. Output encoding

### TC-16-SEC-2.1 — The callback error value is never rendered raw

| Field | Value |
|---|---|
| Description | The `error` and `provider` values are URL-controlled; interpolating them into copy turns a failed sign-in into reflected XSS. |
| Preconditions | A signed-out visitor. |
| Test data | `/auth/callback?error=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E&provider=%3Cscript%3Ealert(2)%3C%2Fscript%3E` |
| Steps | 1. Open that URL.<br>2. Read the rendered banner text and the page DOM.<br>3. Watch for any dialog or script execution. |
| Expected result | `/login` shows the generic banner `Не удалось войти через провайдера. Попробуйте снова.`; the DOM contains no `<img`, `onerror`, or `<script` node originating from the query; no alert fires; the raw payload text appears nowhere on screen. |
| Status | Not run |

---

## 3. Handoff-code handling

### TC-16-SEC-3.1 — The handoff code is single-use

| Field | Value |
|---|---|
| Description | A code that can be presented twice is a bearer credential in a URL that anyone with the browser history can spend. |
| Preconditions | The valid handoff code was exchanged once successfully. |
| Test data | `POST /api/v1/auth/oauth/exchange` `{"code": "hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847"}` |
| Steps | 1. Exchange the code (first use).<br>2. Exchange the same code again.<br>3. Count the sessions issued for the account. |
| Expected result | Step 1 answers `200 OK`; step 2 answers `400` with `{"error_code": "INVALID_OR_EXPIRED_OAUTH_CODE", …}` and no token fields; exactly one session was issued in total. |
| Status | Not run |

### TC-16-SEC-3.2 — The handoff code and tokens never appear in a URL or log

| Field | Value |
|---|---|
| Description | A token in a URL leaks through history, `Referer` and every access log on the path; the handoff code must also never be persisted where it can be replayed. |
| Preconditions | Log capture on backend and nginx; a clean browser profile; a completed OAuth sign-in. |
| Test data | The full sign-in from `/login` through `/auth/callback` to the app shell; grep terms: the code value, `access_token`, `refresh_token`, the JWT prefix `eyJ` |
| Steps | 1. Complete an OAuth sign-in end to end.<br>2. Read every URL in the browser history and the current address bar.<br>3. Grep the backend and nginx logs for the code and the token values. |
| Expected result | No access or refresh token appears in any URL, history entry, `Referer`, or log line; the handoff code appears in no persisted log line; after the exchange the callback entry is replaced in history, so the spent code is not reachable from the address bar or Back. |
| Status | Not run |

---

## 4. CSRF state

### TC-16-SEC-4.1 — A callback with an invalid or missing state is rejected

| Field | Value |
|---|---|
| Description | Without state validation an attacker can drive a victim's browser through a callback of the attacker's choosing and land them in the attacker's account. |
| Preconditions | No account exists for provider identity P1; the callback is called directly. |
| Test data | `GET /api/v1/auth/oauth/yandex/callback?code=provider_code_x&state=` (missing), `&state=forged-state-value` (never minted), and a state already consumed once |
| Steps | 1. Call the callback with no `state`.<br>2. Call it with a forged `state`.<br>3. Call it with a state that was already consumed.<br>4. After each, count accounts, identities and handoff codes. |
| Expected result | Each of the three answers `302` to `<frontend>/auth/callback?error=oauth_failed&provider=yandex` — never a redirect carrying a `code`; zero accounts, zero identities and zero handoff codes were created; no session is issued and the failure reason is not distinguishable between the three. |
| Status | Not run |

---

## 5. Abuse / rate limiting

### TC-16-SEC-5.1 — Repeated OAuth requests are rate-limited

| Field | Value |
|---|---|
| Description | Without a bound, the exchange is a free guessing oracle over the code space and `start` is a state-row flood. |
| Preconditions | The Postgres-backed rate limiter is wired with the configured window; the caller's source is the rightmost `X-Forwarded-For` hop. |
| Test data | `OAUTH_RATE_LIMIT_MAX_REQUESTS=40` per `OAUTH_RATE_LIMIT_WINDOW_SECONDS=60`; 45 requests from one source to each of `start`, `callback`, `exchange` |
| Steps | 1. Send 45 requests to `/api/v1/auth/oauth/yandex/start` from one source inside one window.<br>2. Repeat against the callback and the exchange.<br>3. From a second source, send one request to each leg during the same window.<br>4. Wait out the window and retry from the first source. |
| Expected result | In each leg the first 40 are served and the remainder answer `429` with `{"error_code": "OAUTH_RATE_LIMITED", "message": "<generic text>"}`; the buckets are per (leg, source), so the second source in step 3 is served normally and one leg's flood does not throttle another; after the window the first source is served again; the refusal names neither the source nor the count. |
| Status | Not run |

---

## 6. Mass assignment

### TC-16-SEC-6.1 — Privileged fields in the exchange body are ignored

| Field | Value |
|---|---|
| Description | If the request body can reach the account row, the first OAuth sign-in is a self-service privilege grant. |
| Preconditions | No account exists for provider identity P1; a valid handoff code for P1 exists. |
| Test data | Body `{"code": "<valid code>", "is_admin": true, "role": "admin", "id": "00000000-0000-4000-8000-000000000000", "email": "attacker@evil.test", "password_hash": "x"}` |
| Steps | 1. POST the exchange with that body.<br>2. Read the persisted account row column by column. |
| Expected result | `200 OK`; the persisted account has the provider-asserted email `qa.oauth@textery.test`, a server-generated id, no admin/role elevation, and an empty password hash it did not take from the body; every injected field was ignored and none is echoed in the response. |
| Status | Not run |

---

## 7. Error-path disclosure

### TC-16-SEC-7.1 — Failure responses carry no internal detail

| Field | Value |
|---|---|
| Description | A stack frame, an SQL fragment or raw upstream provider text in an error body maps the stack for an attacker — and the provider email and handoff code are the two values that must never come back out. |
| Preconditions | Sentinels can be seeded into the store error, the provider response and the code value; log capture is attached. |
| Test data | Sentinels `relation "handoff_codes" does not exist`, `/app/usecase/src/auth/oauth/exchange_handoff_code.py`, `CompleteOAuthCallback`, provider body `{"error":"invalid_grant","hint":"SENTINEL-UPSTREAM"}`, code `hc_SENTINEL_CODE_VALUE`, email `qa.oauth@textery.test` |
| Steps | 1. Trigger the store-unavailable path with its sentinel seeded.<br>2. Trigger a provider error and a provider timeout on the callback.<br>3. Trigger an exchange 5xx.<br>4. Read every response body and the captured log output. |
| Expected result | Every failure body matches `{"error_code": "<CODE>", "message": "<generic text>"}` — `INTERNAL_ERROR` with `An unexpected error occurred. Please try again.` for the 5xx paths, and the callback legs redirect to `?error=oauth_failed`; no sentinel string, stack trace, SQL fragment, internal class name, file path or raw upstream provider text appears in any body; the provider email and the handoff code appear in neither the responses nor the captured log output. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the OAuth callback` | `GET /api/v1/auth/oauth/{provider}/callback` and the frontend `/auth/callback` |
| `a handoff code` | opaque single-use short-TTL code |
| `the exchange` | `POST /api/v1/auth/oauth/exchange` |
| `the start / callback / exchange endpoints` | the three `/api/v1/auth/oauth/*` routes |
