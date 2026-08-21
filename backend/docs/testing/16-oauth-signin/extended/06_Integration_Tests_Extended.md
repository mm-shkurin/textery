<!-- COPIED FILE. Source of truth: ProductSpecification/stories/16-oauth-signin/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# OAuth sign-in — Integration Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

Exercised through the provider fake (`OAUTH_PROVIDER=fake`) over the three
`/api/v1/auth/oauth/*` legs.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Provider identity P1 | provider `yandex`, subject `1000000000000123`, email `qa.oauth@textery.test` |
| Account A | id `4c8f1a92-6d3b-4e77-9a10-5b2f8c7d1e04`, email `qa.oauth@textery.test` |
| Backend callback | `GET /api/v1/auth/oauth/{provider}/callback?code=<provider code>&state=<minted state>` |
| Exchange call | `POST /api/v1/auth/oauth/exchange` body `{"code": "<handoff code>"}` |
| Session body shape | `{"access_token": "…", "refresh_token": "…", "access_token_expires_at": "…", "refresh_token_expires_at": "…"}` |

---

## 1. Returning user

### TC-16-INT-1.1 — A returning provider identity resolves to the existing account

| Field | Value |
|---|---|
| Description | Auto-create must fire only once per identity; a second row on the second sign-in would split the user's documents across two accounts. |
| Preconditions | Account A already exists from a prior sign-in, with the `(yandex, 1000000000000123)` identity row. |
| Test data | Provider identity P1; a fresh handoff code from a new callback |
| Steps | 1. Record the account and identity row counts and account A's id.<br>2. Run `start` → `callback` again for P1 and capture the new handoff code.<br>3. Exchange it.<br>4. Re-count accounts and identities for P1. |
| Expected result | `200 OK` with the four session fields; the access token carries account A's id `4c8f1a92-6d3b-4e77-9a10-5b2f8c7d1e04`; the account and identity row counts are unchanged from step 1 — no duplicate account, no second identity row, no new email. |
| Status | Not run |

---

## 2. Both providers

### TC-16-INT-2.1 — The same email via two different providers stays two identities

| Field | Value |
|---|---|
| Description | Linking is deferred, so the same address arriving from two providers must resolve per identity rather than being silently merged — an implicit merge here is a cross-provider account takeover. |
| Preconditions | Both `vk` and `yandex` are wired in the provider registry; each fake asserts the same email. |
| Test data | `(vk, 3000000000000789)` and `(yandex, 1000000000000123)`, both asserting `qa.oauth@textery.test` |
| Steps | 1. Complete `start` → `callback` → `exchange` through the VK fake.<br>2. Complete the same three legs through the Yandex fake.<br>3. Read the identity rows and the account id each access token carries. |
| Expected result | Two identity rows exist — `(vk, 3000000000000789)` and `(yandex, 1000000000000123)` — each resolving per its own provider identity; no linking or merge is attempted between them; each exchange answers `200 OK` with the four session fields. |
| Status | Not run |
| Note | The current backend refuses an auto-create whose email already belongs to another account, so the second provider's leg lands on `?error=oauth_failed` until account-linking ships; the invariant under test either way is that neither provider's identity silently adopts the other's account. |
