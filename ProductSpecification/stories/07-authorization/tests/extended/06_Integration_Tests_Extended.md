> These are additional edge case tests. Implement after core tests pass.

# Authorization — Integration Tests (Extended)

Shared test data:

| Name | Value |
|---|---|
| Account V (verified) | `qa.int.verified@textery.test` / `Qa!IntV2026` |
| Refresh endpoint | `POST /api/v1/auth/refresh` |
| Protected endpoint | `GET /api/v1/auth/me` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic client-safe text>"}` |

---

## TC-07-INT-E1 — Multiple concurrent refresh calls with the same refresh token

| Field | Value |
|---|---|
| Description | Real clients fire this by accident: two tabs, or two queued requests, both hit a `401` and both refresh with the same stored token. The pipeline must land on one defined outcome rather than a race — a `500`, a half-written token row, or two tokens where the DB expected one. |
| Preconditions | A login for account V has returned a valid, unexpired refresh token; no other refresh is in flight. |
| Test data | Two `POST /api/v1/auth/refresh` requests carrying the identical `{"refresh_token": "…"}`, fired via `asyncio.gather` |
| Steps | 1. Fire both refresh requests at the same instant.<br>2. Record both statuses and bodies.<br>3. Present every returned `access_token` to `GET /api/v1/auth/me`.<br>4. Inspect the stored refresh-token rows for the account. |
| Expected result | Either both answer `200 OK`, each with a usable `access_token` that step 3 accepts with `200 OK`, or one answers `200 OK` and the other `401 {"error_code": "INVALID_REFRESH_TOKEN", ...}`; in neither case does any request answer `500`; step 4 shows the stored token state is consistent — no duplicated or partially-written row, and the account remains able to refresh afterwards. |
| Status | Not run |
