# OAuth sign-in — API Tests

> **Implementation Order**: sequential TDD — `start` redirect + provider validation, then
> `exchange` branches (replay, expiry, size, empty), concurrency + atomicity, then account
> auto-creation and identity resolution.

Endpoints: `GET /api/v1/auth/oauth/{provider}/start`, `GET /api/v1/auth/oauth/{provider}/callback`,
`POST /api/v1/auth/oauth/exchange`.
Contracts: `ProductSpecification/api-specs/oauth_start.yaml`, `oauth_callback.yaml`, `oauth_exchange.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Provider identity P1 | provider `yandex`, subject `1000000000000123`, email `qa.oauth@textery.test` |
| Account A (created for P1) | id `4c8f1a92-6d3b-4e77-9a10-5b2f8c7d1e04`, email `qa.oauth@textery.test` |
| Handoff code H1 | `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847` (opaque, single-use, TTL `OAUTH_HANDOFF_CODE_TTL_SECONDS=300`) |
| Handoff-code length cap | `512` characters (`MAX_HANDOFF_CODE_LENGTH`) |
| Session body shape | `{"access_token": "...", "refresh_token": "...", "access_token_expires_at": "...", "refresh_token_expires_at": "..."}` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| Exchange refusal | `400 Bad Request`, `error_code = INVALID_OR_EXPIRED_OAUTH_CODE` |

---

## 1. Start endpoint

### TC-16-API-1.1 — Start redirects to the provider

| Field | Value |
|---|---|
| Description | The button target must hand the browser to the provider with the handshake parameters minted server-side — a client that has to supply `client_id`, `redirect_uri`, `scope` or `state` is a leaked-secret design. |
| Preconditions | `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `YANDEX_REDIRECT_URI` and `OAUTH_FRONTEND_CALLBACK_URL` are set in `infra/.env`; the backend booted. |
| Test data | `GET /api/v1/auth/oauth/yandex/start`, no query parameters, no auth header |
| Steps | 1. `GET /api/v1/auth/oauth/yandex/start` without following redirects.<br>2. Read the `Location` header.<br>3. Query the OAuth-state store for the row minted by this call. |
| Expected result | `302 Found`; `Location` starts with `https://oauth.yandex.ru/authorize?` and carries `response_type=code`, the configured `client_id`, the configured `redirect_uri` and a `state` value; the same `state` exists as a server-side row; the response body is empty and no client secret appears anywhere in the response. |
| Status | Not run |

### TC-16-API-1.2 — Unknown provider is rejected

| Field | Value |
|---|---|
| Description | An unknown slug must be a rejected value, never silently defaulted to a configured provider's handshake. |
| Preconditions | Backend running with the provider registry wired. |
| Test data | `provider = twitch` |
| Steps | 1. `GET /api/v1/auth/oauth/twitch/start` without following redirects.<br>2. Read the status, body and headers. |
| Expected result | A refusal in the `{error_code, message}` shape carrying `error_code = UNKNOWN_OAUTH_PROVIDER`; no `Location` header and no redirect to any provider. `oauth_start.yaml` declares `404`; the current handler falls through the status map and answers `400` — the status must be one of these two consistently, and never `302`. |
| Status | Not run |

---

## 2. Exchange — validation & safety

### TC-16-API-2.1 — A valid handoff code returns a session

| Field | Value |
|---|---|
| Description | The exchange is the only place a real token appears; its body must be interchangeable with `/auth/login` so the frontend keeps one session boundary. |
| Preconditions | Handoff code H1 freshly minted for account A and unspent. |
| Test data | `POST /api/v1/auth/oauth/exchange` body `{"code": "hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847"}` |
| Steps | 1. POST the body above.<br>2. Compare the response body's key set against a `POST /api/v1/auth/login` response. |
| Expected result | `200 OK`; `Content-Type: application/json`; body carries exactly `access_token`, `refresh_token`, `access_token_expires_at`, `refresh_token_expires_at`, all non-empty; the key set is identical to the login response's; the access token decodes to account A's id `4c8f1a92-6d3b-4e77-9a10-5b2f8c7d1e04`. |
| Status | Not run |

### TC-16-API-2.2 — A replayed code is rejected

| Field | Value |
|---|---|
| Description | A one-time code that survives its first use is a reusable credential sitting in a URL — a Back or refresh onto the callback would mint a second session. |
| Preconditions | Handoff code H1 was exchanged once successfully (TC-16-API-2.1). |
| Test data | The same body `{"code": "hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847"}` |
| Steps | 1. POST the exchange body a second time.<br>2. Count the sessions issued for account A. |
| Expected result | `400 Bad Request`, body `{"error_code": "INVALID_OR_EXPIRED_OAUTH_CODE", "message": "<generic text>"}`; no token field in the body; exactly one session was ever issued for H1. |
| Status | Not run |

### TC-16-API-2.3 — An expired code is rejected at the TTL boundary

| Field | Value |
|---|---|
| Description | The TTL must be evaluated on both sides of the boundary against an injectable clock; a code accepted after expiry makes the short TTL decorative. |
| Preconditions | Handoff code H2 minted at `T0` with TTL `300 s`; the clock is injectable. |
| Test data | H2 = `hc_5b1e0d73a8c2419e8f6d4c3b2a190e5f`; clock pinned to `T0 + 299 s`, then to `T0 + 300 s` (`expires_at` itself already counts as expired — the guard is `>=`) |
| Steps | 1. Mint H2, pin the clock to `T0 + 299 s`, exchange H2.<br>2. Mint an equivalent code H3, pin the clock to `T0 + 300 s`, exchange H3. |
| Expected result | Step 1 answers `200 OK` with the four session fields; step 2 answers `400` with `error_code = INVALID_OR_EXPIRED_OAUTH_CODE` and no token. |
| Status | Not run |

### TC-16-API-2.4 — An over-length code is rejected before lookup

| Field | Value |
|---|---|
| Description | An unbounded code value is an amplification lever against the code index; the bound must be checked before any store read. |
| Preconditions | Backend running; the handoff-code store is instrumented to count lookups. |
| Test data | `code` = `"a"` × 513 (one over the `512` cap); the boundary value `"a"` × 512 must still reach the lookup |
| Steps | 1. POST the exchange with the 513-character code.<br>2. Read the store's lookup counter. |
| Expected result | `400 Bad Request` with `error_code = INVALID_OR_EXPIRED_OAUTH_CODE`; the store lookup counter did not increase; no session issued. |
| Status | Not run |

### TC-16-API-2.5 — Concurrent exchanges of one code yield exactly one session

| Field | Value |
|---|---|
| Description | Two tabs — or two instances — redeeming the same code must not both win; a check-then-delete would issue two sessions from one one-time code. |
| Preconditions | One freshly minted, unspent code H4; two backend instances share the handoff-code store; both requests are held at the redeem point. |
| Test data | H4 = `hc_2d7a4f019b6c48e3a5f01c8b7e6d3a29`; two simultaneous `POST /api/v1/auth/oauth/exchange` with that code, one per instance |
| Steps | 1. Hold both requests at the redeem point.<br>2. Release both simultaneously.<br>3. Record both responses and the store's statement log. |
| Expected result | Exactly one response is `200 OK` with the four session fields; the other is `400` with `error_code = INVALID_OR_EXPIRED_OAUTH_CODE`; never two `200`s and never two sessions; the redemption is a single atomic compare-and-delete statement, not a read followed by a separate delete. |
| Status | Not run |

### TC-16-API-2.7 — An empty or missing code is rejected server-side

| Field | Value |
|---|---|
| Description | The client-side guard is not the boundary; a direct caller sending an empty or absent `code` must still be refused without a session. |
| Preconditions | Backend running. |
| Test data | Bodies `{"code": ""}` and `{}` |
| Steps | 1. POST `{"code": ""}`.<br>2. POST `{}` (no `code` key). |
| Expected result | Step 1 answers `400` with `error_code = INVALID_OR_EXPIRED_OAUTH_CODE`; step 2 answers `422` from the request-schema boundary (`code` is required); neither body carries a token and no session is issued. |
| Status | Not run |

### TC-16-API-2.6 — A code minted on one instance is redeemable on another

| Field | Value |
|---|---|
| Description | The code store is shared, not per-process; a first legitimate exchange landing on another replica must not spuriously fail. |
| Preconditions | Two backend instances behind the load balancer share one handoff-code store; account A exists. |
| Test data | H5 minted on instance 1, exchanged against instance 2 within 1 second of minting |
| Steps | 1. Complete a callback on instance 1 and capture the minted code from the redirect.<br>2. Immediately POST the exchange directly to instance 2. |
| Expected result | `200 OK` with the four session fields; no `400`; the code is absent from the store afterwards. |
| Status | Not run |

---

## 3. Account resolution

### TC-16-API-3.1 — First sign-in auto-creates one verified account

| Field | Value |
|---|---|
| Description | The provider asserts the email, so nothing may stand between a first OAuth sign-in and a usable session — and exactly one account may result. |
| Preconditions | No account and no OAuth identity exist for provider identity P1. |
| Test data | Provider identity P1; the handoff code minted by its callback |
| Steps | 1. Complete the callback for P1 and capture the handoff code.<br>2. Exchange it.<br>3. Query the accounts table for `qa.oauth@textery.test`. |
| Expected result | `200 OK` with the four session fields; exactly one account row exists with email `qa.oauth@textery.test`, marked verified, with no verification code issued or sent; the returned access token is accepted by `GET /api/v1/auth/me`. |
| Status | Not run |

### TC-16-API-3.2 — Concurrent first sign-ins for one identity create one account

| Field | Value |
|---|---|
| Description | A plain check-then-insert races: the unique `(provider, subject)` constraint, not timing, must be what forces one account. |
| Preconditions | No account exists for provider identity P1; two first-time exchanges for P1 are held before the resolve step. |
| Test data | Provider identity P1 (`yandex` / `1000000000000123`); two handoff codes minted for the same identity |
| Steps | 1. Hold both exchanges before account resolution.<br>2. Release both simultaneously.<br>3. Count rows in the accounts and OAuth-identity tables for P1. |
| Expected result | Both requests answer `200 OK`; exactly one account row and exactly one `(yandex, 1000000000000123)` identity row exist; both access tokens carry the same account id — the loser resolved to the existing account rather than creating a duplicate. |
| Status | Not run |
| Note | The unique constraint (not timing) forces single-account — a plain check-then-insert goes red. |

### TC-16-API-3.3 — Email case / normalization / locale variance resolves to one account

| Field | Value |
|---|---|
| Description | Case-folding under a Turkish locale maps `I` to `ı`, splitting one human into two accounts; NFD/NFC variance does the same for accented mail. Folding must be invariant-locale and normalization NFC. |
| Preconditions | The account-resolution key is the normalized provider email; the process can be run under `tr-TR`. |
| Test data | `QA.Oauth@textery.test` vs `qa.oauth@textery.test`; the Turkish pair `IRINA@textery.test` vs `irina@textery.test`; `renée@textery.test` in NFC vs NFD (`e` + U+0301) |
| Steps | 1. Exchange a handoff code for each casing variant.<br>2. Exchange a handoff code for each normalization variant.<br>3. Read back the stored email bytes. |
| Expected result | Each pair resolves to one single account id (one account row, not two), including under `tr-TR`; the stored multibyte email round-trips byte-exact in NFC as `renée@textery.test` — no mangling, no `?`, no `�`. |
| Status | Not run |
| Note | Turkish I/İ forces invariant-locale folding; round-trip forces NFC without mangling non-ASCII. |

### TC-16-API-3.7 — A large provider subject id is not truncated

| Field | Value |
|---|---|
| Description | A subject carried as a JSON number loses precision above 2^53, collapsing two distinct users into one account — takeover by rounding. |
| Preconditions | The provider fake can assert an arbitrary subject; no identity exists for either subject. |
| Test data | Subjects `9007199254740993` and `9007199254740995` (both above `Number.MAX_SAFE_INTEGER`) |
| Steps | 1. Exchange a handoff code for subject `9007199254740993`.<br>2. Exchange a handoff code for subject `9007199254740995`.<br>3. Read both stored subject values. |
| Expected result | Two distinct accounts and two distinct identity rows; the stored subjects are exactly `9007199254740993` and `9007199254740995`, carried as strings — not rounded to `9007199254740992`/`9007199254740996`, and not equal to each other. |
| Status | Not run |

### TC-16-API-3.8 — OAuth email colliding with an existing password account does not overwrite it

| Field | Value |
|---|---|
| Description | Linking is deferred, so the load-bearing guarantee is that the neighbouring password account is left untouched — no conversion, no credential change, no takeover. |
| Preconditions | An email+password account exists for `qa.oauth@textery.test` with a known password hash; no OAuth identity exists for P1. |
| Test data | Existing account `qa.oauth@textery.test` / `Qa!Oauth2026`; provider identity P1 asserting the same email |
| Steps | 1. Record the existing account's id, password hash and verified flag.<br>2. Complete the OAuth callback for P1 and exchange the handoff code.<br>3. Re-read the pre-existing account row.<br>4. `POST /api/v1/auth/login` with the original password. |
| Expected result | The OAuth sign-in produces a NEW, distinct account with a different account id (linking is deferred); the pre-existing row's id, password hash and verified flag are identical to step 1; the step-4 login still answers `200 OK` with a session. |
| Status | Not run |
| Note | Deferred-linking makes "leave the neighbour intact" load-bearing — also the takeover guard. The current backend instead refuses this callback with the generic `?error=oauth_failed` redirect; whichever behaviour is intended, the password account must be provably untouched. |

### TC-16-API-3.9 — A failed session issue leaves no orphan account

| Field | Value |
|---|---|
| Description | An account created but never signed into is unreachable for the user and a duplicate on their next attempt — the whole unit must be all-or-nothing. |
| Preconditions | Provider identity P1 has no account; the token-issue step is instrumented to fail after the account write. |
| Test data | Provider identity P1; injected failure at the session-issue step |
| Steps | 1. Complete the callback and exchange the handoff code with the failure injected.<br>2. Query the accounts and OAuth-identity tables for P1. |
| Expected result | `500` with `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; zero account rows and zero identity rows for P1 — the unit rolled back completely. |
| Status | Not run |

### TC-16-API-3.10 — Recovery after a lost exchange response

| Field | Value |
|---|---|
| Description | A network drop after the server committed must be a recoverable path, not a dead end that leaves a duplicate account behind. |
| Preconditions | An exchange for P1 committed a session; its response was dropped before reaching the client. |
| Test data | The spent code from the dropped call; a fresh sign-in from `/login` producing a new handoff code |
| Steps | 1. Exchange a code and drop the response in transit.<br>2. Re-POST the same code (the client's blind retry).<br>3. Restart sign-in from `/login` and exchange the fresh code.<br>4. Count accounts and identities for P1. |
| Expected result | Step 2 answers `400` with `error_code = INVALID_OR_EXPIRED_OAUTH_CODE` (recoverable, not a crash); step 3 answers `200 OK` with a usable session; exactly one account and one identity row exist for P1, and no orphaned session remains. |
| Status | Not run |

### TC-16-API-3.4 — A code that yields no session is not burned

| Field | Value |
|---|---|
| Description | Redeem and issue must commit together; a code silently consumed by a failed issue strands the user with a dead credential. |
| Preconditions | Handoff code H6 is valid and unspent; the session-issue step fails once, then is restored. |
| Test data | H6 = `hc_8e2c6b40d19f47aab3c5178e0d926f4a`; failure injected on the first attempt only |
| Steps | 1. Exchange H6 with the issue failure injected.<br>2. Remove the injected failure.<br>3. Exchange H6 again. |
| Expected result | Step 1 answers `500` with the generic `{error_code, message}` body; step 3 answers `200 OK` with the four session fields — the code was not consumed by the failed attempt. |
| Status | Not run |

### TC-16-API-3.5 — Extra request fields cannot over-bind on auto-create

| Field | Value |
|---|---|
| Description | If the exchange body can carry account attributes, a caller writes their own account row on first sign-in. Only provider-asserted claims may bind. |
| Preconditions | No account exists for provider identity P1. |
| Test data | Body `{"code": "<valid code>", "email": "attacker@evil.test", "id": "00000000-0000-4000-8000-000000000000", "is_admin": true, "is_verified": false}` |
| Steps | 1. POST the exchange with the body above.<br>2. Read the created account row. |
| Expected result | `200 OK`; the created account's email is the provider-asserted `qa.oauth@textery.test`, not `attacker@evil.test`; its id is server-generated, not `00000000-0000-4000-8000-000000000000`; no privileged flag was set from the body; the extra keys are ignored and not echoed back. |
| Status | Not run |

### TC-16-API-3.6 — Sign-in failure copy does not reveal account existence

| Field | Value |
|---|---|
| Description | A response that differs between "this identity has an account" and "it does not" is an enumeration oracle over the user base. |
| Preconditions | Provider identity P1 has an account; provider identity P2 (`yandex` / `2000000000000456`, `qa.nobody@textery.test`) has none. |
| Test data | An invalid/expired code for each of P1 and P2 |
| Steps | 1. Exchange a failing code for P1 and capture the full response.<br>2. Exchange a failing code for P2 and capture the full response.<br>3. Diff status, headers (bar `Date`) and body. |
| Expected result | Both answer `400` with exactly `{"error_code": "INVALID_OR_EXPIRED_OAUTH_CODE", "message": "<the same generic text>"}`; the two responses are identical bar `Date`; neither names the email nor whether an account exists. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the VK start endpoint` | `GET /api/v1/auth/oauth/vk/start` |
| `the exchange` | `POST /api/v1/auth/oauth/exchange` `{ code }` |
| `a handoff code` | opaque single-use short-TTL code minted by the provider callback |
| `a session ... shape as email+password login` | `{ access_token, refresh_token, access_token_expires_at, refresh_token_expires_at }` |
| `a controlled clock` | injectable clock pinning the TTL boundary |
| `different instances` | multiple backend replicas over the shared handoff-code store |
