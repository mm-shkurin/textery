# OAuth sign-in — Integration Tests

Exercise the backend↔provider handshake through a provider fake. `provider` ∈ `vk | yandex`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Provider fake | `OAUTH_PROVIDER=fake` (`FakeOAuthProvider`), standing in for the Yandex token + info endpoints |
| Provider identity P1 | provider `yandex`, subject `1000000000000123`, email `qa.oauth@textery.test` (verified) |
| Backend callback | `GET /api/v1/auth/oauth/yandex/callback?code=<provider code>&state=<minted state>` |
| Frontend callback base | `OAUTH_FRONTEND_CALLBACK_URL` = `http://localhost/auth/callback` |
| Failure redirect | `…/auth/callback?error=oauth_failed&provider=yandex` |
| Success redirect | `…/auth/callback?code=<opaque handoff code>&provider=yandex` |
| Provider timeout | the adapter's `httpx` client timeout, `10.0 s` |

---

## 1. Provider success flow

### TC-16-INT-1.1 — A valid provider authorization completes sign-in

| Field | Value |
|---|---|
| Description | The three legs must chain: state minted at `start` validates at `callback`, and the code the callback mints is the one the exchange spends. A break anywhere here is an unsignable-in user. |
| Preconditions | Provider fake configured to authorize P1 and return the verified email; no account exists for P1. |
| Test data | Provider identity P1; provider code `fake_provider_code_1`; the `state` captured from `start` |
| Steps | 1. `GET /api/v1/auth/oauth/yandex/start` and capture `state` from the `Location`.<br>2. `GET /api/v1/auth/oauth/yandex/callback?code=fake_provider_code_1&state=<state>` without following redirects.<br>3. Parse the `Location` and extract `code`.<br>4. `POST /api/v1/auth/oauth/exchange` with that code. |
| Expected result | Step 2 answers `302` with `Location` = `http://localhost/auth/callback?code=<opaque>&provider=yandex`, carrying a handoff code and no token and no `error`; step 4 answers `200 OK` with `access_token`, `refresh_token`, `access_token_expires_at`, `refresh_token_expires_at`, all non-empty; exactly one account exists for `qa.oauth@textery.test`. |
| Status | Not run |

---

## 2. Provider error handling

### TC-16-INT-2.1 — A provider error is surfaced as a callback error

| Field | Value |
|---|---|
| Description | A cancelled or failed provider authorization must end as one generic error redirect — not a 500, not a half-created account. |
| Preconditions | Provider fake returns an error / the user cancels; no account exists for P1. |
| Test data | `GET /api/v1/auth/oauth/yandex/callback?error=access_denied&state=<minted state>`, and a run where the fake's token endpoint answers `400 invalid_grant` |
| Steps | 1. Call the backend callback with the provider's `error` leg.<br>2. Repeat with the fake's token exchange failing.<br>3. After each, count accounts, identities and handoff codes. |
| Expected result | Both answer `302` to `http://localhost/auth/callback?error=oauth_failed&provider=yandex` — no `code` parameter, no token anywhere in the URL; zero accounts, zero identities and zero handoff codes created; no session issued; the two failures are indistinguishable to the client. |
| Status | Not run |

### TC-16-INT-2.2 — A provider that returns no verified email is rejected

| Field | Value |
|---|---|
| Description | The account is auto-created without a verification step precisely because the provider asserts the email; without one, we would create an account keyed on nothing trustworthy. |
| Preconditions | Provider fake configured to return an identity with no email, then an empty email, then an unverified one. |
| Test data | Info responses `{"id": "1000000000000123"}` (no email), `{"id": "…", "default_email": ""}`, and an identity flagged unverified |
| Steps | 1. Run the callback for each of the three info responses.<br>2. After each, read the `Location` and count accounts and identities. |
| Expected result | Each answers `302` to `…/auth/callback?error=oauth_failed&provider=yandex`; no handoff code is minted; zero accounts and zero identities are auto-created in any of the three runs. |
| Status | Not run |

---

## 3. Provider timeout

### TC-16-INT-3.1 — A slow provider token exchange fails cleanly

| Field | Value |
|---|---|
| Description | A hung upstream must not hold a DB connection or leave a half-finished handshake behind; a client rebuilt per call plus a retry burst is how one slow provider becomes an outage. |
| Preconditions | Provider fake delays its token response past the adapter timeout; connection-pool checkout metrics and outbound request counts are captured at baseline. |
| Test data | Fake token endpoint sleeps `15 s` against the `10.0 s` client timeout; baseline pool checkouts recorded before the call |
| Steps | 1. Record the pool checkout count and the shared HTTP client's identity.<br>2. Call the backend callback with a valid state so the provider token exchange is attempted.<br>3. Read the response once the timeout fires.<br>4. Count accounts, identities and handoff codes; re-read the pool checkout count; count outbound requests to the fake. |
| Expected result | The request ends at the timeout with `302` to `…/auth/callback?error=oauth_failed&provider=yandex`; no partial account, no identity and no orphan handoff code remain; the pool checkout count returns to its baseline (no leaked in-flight hold); the outbound request count is exactly `1` — the token exchange was not auto-retried; the HTTP client is the shared one, not a fresh instance per call. |
| Status | Not run |
| Note | The backend must NOT auto-retry the provider token exchange in a synchronized burst; if a transient retry is added later, it requires backoff+jitter / capped attempts (own guard). |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the provider fake` | test double for the VK/Yandex OAuth endpoints |
| `the backend callback` | `GET /api/v1/auth/oauth/{provider}/callback` |
| `the frontend callback` | `/auth/callback?code=…` or `?error=…` |
| `the exchange` | `POST /api/v1/auth/oauth/exchange` |
