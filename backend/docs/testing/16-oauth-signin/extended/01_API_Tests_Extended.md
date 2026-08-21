<!-- COPIED FILE. Source of truth: ProductSpecification/stories/16-oauth-signin/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# OAuth sign-in — API Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

Endpoints: `POST /api/v1/auth/oauth/exchange`, `GET /api/v1/auth/oauth/{provider}/start`.
Contracts: `ProductSpecification/api-specs/oauth_exchange.yaml`, `oauth_start.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Valid handoff code | `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847` |
| Session body shape | `{"access_token": "…", "refresh_token": "…", "access_token_expires_at": "…", "refresh_token_expires_at": "…"}` |
| Stored session | `sessionStorage.authSession` holding the access + refresh token |
| Terminal error card | testid `oauth-callback-error`, heading `Не удалось завершить вход` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |

---

## 1. Exchange response evolution

### TC-16-API-1.1 — An unknown extra field in the exchange response is ignored

| Field | Value |
|---|---|
| Description | The backend must be able to add a response field without breaking every deployed client; a strict parser turns an additive change into a sign-in outage. |
| Preconditions | A signed-out visitor on `/auth/callback` with the valid code; the exchange mock resolves a session plus an unknown field. |
| Test data | `200` body: the four session fields plus `{"account_tier": "pro", "issued_by": "auth-2"}` |
| Steps | 1. Open the callback with the valid code and that response.<br>2. Read `sessionStorage.authSession` and the route. |
| Expected result | The sign-in succeeds: `authSession` holds the access and refresh token from the response and the app shell is reached; the extra keys are absent from the stored session and cause no error — the body is not rejected. |
| Status | Not run |

### TC-16-API-1.2 — A 200 exchange missing a usable token is treated as failure

| Field | Value |
|---|---|
| Description | A `200` with no usable token is a broken success; storing it signs the user into an app that will behave as signed out. |
| Preconditions | A signed-out visitor on `/auth/callback` with the valid code. |
| Test data | `200` bodies with `access_token` absent, `null`, `""`, and `"   "` |
| Steps | 1. Open the callback with each of the four responses in turn.<br>2. After each, read `sessionStorage` and the screen. |
| Expected result | In all four runs no session is stored (`authSession` absent) and the terminal error card `oauth-callback-error` is shown; the app shell is never reached. |
| Status | Not run |

---

## 2. Provider parameter

### TC-16-API-2.1 — A provider value differing only by case is rejected

| Field | Value |
|---|---|
| Description | Silently normalizing `Yandex` to `yandex` would let a crafted casing reach the handshake and would break the frontend's exact-match provider guard, which only ever sees the lowercase slug. |
| Preconditions | Backend running with the provider registry wired for `yandex`. |
| Test data | `provider = Yandex`, `YANDEX`, `yAnDeX` |
| Steps | 1. `GET /api/v1/auth/oauth/Yandex/start` without following redirects.<br>2. Repeat for `YANDEX` and `yAnDeX`. |
| Expected result | Each is refused with `error_code = UNKNOWN_OAUTH_PROVIDER` in the `{error_code, message}` shape — never a `302` to the provider and never a normalization to `yandex`. `oauth_start.yaml` declares `404`; the current handler answers `400` through the default status mapping. |
| Status | Not run |
