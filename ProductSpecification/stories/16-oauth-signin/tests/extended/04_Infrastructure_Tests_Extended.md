# OAuth sign-in — Infrastructure Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Handoff-code store | the Postgres-backed store behind `HandoffCodeRepository`; DB service `postgres` in `infra/docker-compose.yml` |
| Fresh handoff code | `hc_1c4d9e83b072456fa8d31e5b6c907f2d` |
| Exchange call | `POST /api/v1/auth/oauth/exchange` body `{"code": "<code>"}` |
| Session body shape | `{"access_token": "…", "refresh_token": "…", "access_token_expires_at": "…", "refresh_token_expires_at": "…"}` |

---

## 1. Store recovery

### TC-16-INFRA-1.1 — Exchange recovers after the handoff-code store comes back

| Field | Value |
|---|---|
| Description | Failing closed during an outage is only half the guard: if the pooled connections stay poisoned after recovery, sign-in stays broken long after the store is healthy again. |
| Preconditions | The handoff-code store was stopped, then restarted, for this repo index only; the backend was NOT restarted. |
| Test data | Stop then start the DB service of `infra/docker-compose.yml`; then mint a fresh code `hc_1c4d9e83b072456fa8d31e5b6c907f2d` through a full callback |
| Steps | 1. Stop the store; attempt one exchange and confirm it fails closed.<br>2. Start the store again and wait for it to accept connections.<br>3. Complete a fresh sign-in through `start` → `callback` to mint a new code.<br>4. Exchange that fresh code. |
| Expected result | Step 4 answers `200 OK` with all four session fields non-empty; no `500` and no lingering connection error; the backend recovered without a restart, and the code minted after recovery is redeemed exactly once. |
| Status | Not run |
