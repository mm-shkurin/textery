<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/06_Integration_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Authorization — Integration Tests

This story has no live external API (verification email is mocked, no OAuth provider is
in scope — see `interview.md`), so the usual "external API success/error/timeout"
scenarios don't apply. The one integration seam this story owns end-to-end is the
token-issuance-then-refresh pipeline.

Shared test data for every case below:

| Name | Value |
|---|---|
| Fresh account | `qa.int.pipeline@textery.test` / `Qa!Int2026` |
| Endpoints | `POST /api/v1/auth/register`, `/auth/verify`, `/auth/login`, `/auth/refresh` |
| Protected endpoint | `GET /api/v1/auth/me` with `Authorization: Bearer <access token>` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic client-safe text>"}` |

---

## TC-07-INT-1 — Full Register → Verify → Login → Refresh Pipeline

| Field | Value |
|---|---|
| Description | Each endpoint passing in isolation says nothing about the handoffs between them — the code from register must be the one verify accepts, and the token pair from login must be the one refresh recognises. |
| Preconditions | Backend and Postgres healthy; `qa.int.pipeline@textery.test` is unregistered. |
| Test data | `{"email": "qa.int.pipeline@textery.test", "password": "Qa!Int2026", "confirm_password": "Qa!Int2026"}` |
| Steps | 1. `POST /api/v1/auth/register` and read `verification_code`.<br>2. `POST /api/v1/auth/verify` with that exact code string.<br>3. `POST /api/v1/auth/login` with the same credentials.<br>4. `POST /api/v1/auth/refresh` with the returned `refresh_token`.<br>5. `GET /api/v1/auth/me` with the refreshed `access_token`. |
| Expected result | Step 1 `201 Created` with `is_verified: false` and a 6-digit code string; step 2 `200 OK` `{"is_verified": true}`; step 3 `200 OK` with `access_token` and `refresh_token`; step 4 `200 OK` with a new `access_token`; step 5 `200 OK` returning the profile for `qa.int.pipeline@textery.test`. No step returns `4xx` or `5xx`. |
| Status | Not run |

## TC-07-INT-2 — Refresh Token Reuse After Access Token Expiry

| Field | Value |
|---|---|
| Description | Refresh exists precisely for the moment the access token is dead; a refresh path that requires a live access token is useless in the only case it is needed. |
| Preconditions | A login for the account above has returned a token pair; the injectable clock is advanced past the access token's expiry but well inside the refresh token's. |
| Test data | The `refresh_token` from that login; clock at `access_token_expires_at + 1 minute` |
| Steps | 1. Confirm the old access token is dead: `GET /api/v1/auth/me` with it.<br>2. `POST /api/v1/auth/refresh` with only `{"refresh_token": "…"}` — no `Authorization` header.<br>3. `GET /api/v1/auth/me` with the new access token. |
| Expected result | Step 1 answers `401 UNAUTHORIZED`; step 2 answers `200 OK` with a fresh `access_token` and an `access_token_expires_at` in the future, without any access token being supplied; step 3 answers `200 OK`. |
| Status | Not run |

## TC-07-INT-3 — Login Immediately Usable Against a Protected Route

| Field | Value |
|---|---|
| Description | A token that needs a moment to become valid — replica lag, a cache warm-up — makes the very first post-login request fail for a user who did nothing wrong. |
| Preconditions | The account is verified and unlocked. |
| Test data | Correct credentials; the protected call issued within 100 ms of the login response |
| Steps | 1. `POST /api/v1/auth/login` and capture `access_token`.<br>2. Immediately (< 100 ms, no retry, no sleep) `GET /api/v1/auth/me` with that token. |
| Expected result | Step 2 answers `200 OK` on the first attempt, returning the caller's own profile — never a `401` that would succeed on a retry. |
| Status | Not run |
