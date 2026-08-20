<!-- COPIED FILE. Source of truth: ProductSpecification/stories/16-oauth-signin/tests/04_Infrastructure_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# OAuth sign-in — Infrastructure Tests

Deployment-level guards for the OAuth legs: the shared handoff-code store, the operator
signal on fail-closed branches, and boot-time configuration validation.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Handoff-code store | the Postgres-backed store behind `HandoffCodeRepository` (never in-process) |
| Compose file | `infra/docker-compose.yml`; DB service `postgres` |
| Config source | `infra/.env` — `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `YANDEX_REDIRECT_URI`, `OAUTH_FRONTEND_CALLBACK_URL`, `OAUTH_HANDOFF_CODE_TTL_SECONDS` |
| Valid handoff code | `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847` |
| Exchange call | `POST /api/v1/auth/oauth/exchange` body `{"code": "<code>"}` |
| Generic 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |

---

## 1. Handoff-code store failure

### TC-16-INFRA-1.1 — An exchange fails closed when the code store is unavailable

| Field | Value |
|---|---|
| Description | If the store is down and the exchange still hands out a session, the single-use guarantee has been traded away exactly when it cannot be checked. |
| Preconditions | Backend up; a valid unspent handoff code exists; the code store is then made unreachable. |
| Test data | Stop the DB service (`docker compose -f infra/docker-compose.yml stop postgres`, the compose file for this repo index only); code `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847` |
| Steps | 1. Take the handoff-code store down.<br>2. `POST /api/v1/auth/oauth/exchange` with the valid code.<br>3. Read the response and check whether any token was issued.<br>4. Bring the store back up. |
| Expected result | `500` with `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}`; the body carries no `access_token`/`refresh_token`; no session exists for that account; the failure is not silently downgraded to a success on the unverified path. |
| Status | Not run |

---

## 1a. Failure observability

### TC-16-INFRA-1a.1 — Fail-closed branches emit an attributable operator signal

| Field | Value |
|---|---|
| Description | The code and tokens must never be logged, so the only way a spike in fail-closed sign-ins becomes visible to operators is a metric or a correlation-id-keyed log line. |
| Preconditions | Log/metric capture is attached to the backend; a valid code exists for the success leg. |
| Test data | Failure classes: store unavailable, provider token-exchange timeout; correlation id from the request's `X-Request-Id` |
| Steps | 1. Trigger an exchange with the code store unavailable; capture logs/metrics.<br>2. Trigger a callback with the provider fake timing out; capture logs/metrics.<br>3. Run one successful sign-in; capture logs/metrics. |
| Expected result | Steps 1 and 2 each emit exactly one error-level record (or increment one failure-class counter) carrying the correlation id and the failure class; step 3 emits no such failure record and increments no failure counter; no handoff code, access token, refresh token or provider email appears in any captured line. |
| Status | Not run |
| Note | Because the code/token must never be logged, the operator signal is a metric / correlation id — a spike in fail-closed responses must not be invisible. |

---

## 2. OAuth configuration validation

### TC-16-INFRA-2.1 — Missing OAuth provider config fails fast at startup

| Field | Value |
|---|---|
| Description | A lazy dev-fallback for a redirect target surfaces as a broken handshake at the first production sign-in, long after the deploy that caused it. |
| Preconditions | A working `infra/.env`; the backend can be restarted for this repo index. |
| Test data | Unset, then blank (`""`), each of `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, `YANDEX_REDIRECT_URI`, `OAUTH_FRONTEND_CALLBACK_URL` |
| Steps | 1. Unset one required OAuth setting and start the backend; capture stderr and the exit status.<br>2. Repeat with the setting present but blank.<br>3. Repeat for each of the four settings.<br>4. Restore `infra/.env` and start normally. |
| Expected result | Every run fails at startup with `OAuthConfigurationError` naming the missing variable (e.g. `YANDEX_REDIRECT_URI is not set…see .env.example`); the process does not serve traffic; no default or `localhost` redirect target is substituted, so no sign-in can reach a half-configured provider; step 4 starts cleanly. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the shared handoff-code store` | DB/cache backing the single-use code (never in-process) |
| `a required OAuth provider setting` | `infra/.env` OAuth keys for VK/Yandex |
