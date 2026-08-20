# Authorization — API Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with registration validation (no infrastructure needed), then registration
> happy path + re-run-safety guards, then verify-code, then resend-code, then login
> (validation, lockout, happy path), then refresh.

Endpoints: `POST /api/v1/auth/register`, `/auth/verify`, `/auth/resend-code`,
`/auth/login`, `/auth/refresh`. Contracts: `ProductSpecification/api-specs/auth_register.yaml`,
`auth_verify.yaml`, `auth_resend_code.yaml`, `auth_login.yaml`, `auth_refresh.yaml`.

No parent-resource prerequisite guards apply to this story (no board/column-style
dependency) — the only "guards" are field-level validation and the re-run-safety
scenarios below (mandatory per the Side-Effect & Idempotency Guard Checklist: the
register→code-issue and resend→invalidate-and-reissue sequences both mutate persisted
state and can be re-run by a retrying client).

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account P (pending, unverified) | `qa.auth.pending@textery.test` / `Qa!Auth2026`, `user_id` `3f8c1d92-7a04-4e6b-9c15-8b2d5e7f0a31` |
| Account V (verified) | `qa.auth.verified@textery.test` / `Qa!Verified2026`, `user_id` `9d21b7e4-5c88-4a10-b3f6-1e07c4a95d62` |
| Fresh email (never registered) | `qa.auth.new@textery.test` |
| Valid password | `Qa!Auth2026` (11 chars: digit + upper + lower + special) |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic client-safe text>"}` |
| Code TTL / resend cooldown / lockout threshold | 10 minutes / 60 seconds / 5 consecutive failures |
| Generic 500 body | `{"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again."}` |

---

## 1. Register — Validation

### TC-07-API-1.1 — Reject malformed email

| Field | Value |
|---|---|
| Description | A malformed address must be refused at the field level before any row is written; accepting it would create an unreachable account. |
| Preconditions | No account exists for the value below. |
| Test data | `{"email": "not-an-email", "password": "Qa!Auth2026", "confirm_password": "Qa!Auth2026"}` |
| Steps | 1. `POST /api/v1/auth/register` with that body.<br>2. Query the `users` table for `not-an-email`. |
| Expected result | `400 Bad Request`; body `{"error_code": "INVALID_EMAIL", "message": "The email address is not valid."}`; step 2 returns zero rows. |
| Status | Not run |

### TC-07-API-1.2 — Reject email exceeding the length limit

| Field | Value |
|---|---|
| Description | `email` is capped at 255 characters; an unbounded string is a resource-amplification vector reaching the hash and the DB write. |
| Preconditions | No account exists for the value below. |
| Test data | `email` = `a` × 243 + `@textery.test` (256 characters total), password `Qa!Auth2026` |
| Steps | 1. `POST /api/v1/auth/register` with that email.<br>2. Count rows in `users` for that email. |
| Expected result | `400 Bad Request` with `error_code` `INVALID_EMAIL`; step 2 returns zero rows. |
| Status | Not run |

### TC-07-API-1.3 — Reject password failing the policy

| Field | Value |
|---|---|
| Description | Every arm of the policy (length floor, digit, uppercase, special, length ceiling) must be enforced, not just the ones the happy path happens to exercise. |
| Preconditions | `qa.auth.new@textery.test` is unregistered; `confirm_password` always equals `password`. |
| Test data | `Qa!2026` (7 chars); `Qa!Password` (no digit); `qa!auth2026` (no uppercase); `QaAuth2026a` (no special); `Qa!` + `a` × 126 (129 chars) |
| Steps | 1. `POST /api/v1/auth/register` with the 7-character password.<br>2. Repeat with the no-digit password.<br>3. Repeat with the no-uppercase password.<br>4. Repeat with the no-special password.<br>5. Repeat with the 129-character password. |
| Expected result | Each of the five answers `400 Bad Request` with `{"error_code": "INVALID_PASSWORD", "message": "The password does not meet the password policy."}`. |
| Status | Not run |

### TC-07-API-1.4 — Reject password/confirm_password mismatch

| Field | Value |
|---|---|
| Description | A typo in the confirmation must not create an account whose password the user cannot reproduce. |
| Preconditions | `qa.auth.new@textery.test` is unregistered. |
| Test data | `password` `Qa!Auth2026`, `confirm_password` `Qa!Auth2027` |
| Steps | 1. `POST /api/v1/auth/register` with those two values.<br>2. Count rows in `users` for that email. |
| Expected result | `400 Bad Request`; body `{"error_code": "PASSWORD_MISMATCH", "message": "The password confirmation does not match."}`; step 2 returns zero rows. |
| Status | Not run |

### TC-07-API-1.5 — Ignore server-owned fields in the request body

| Field | Value |
|---|---|
| Description | Mass assignment: an attacker-supplied `is_verified` would skip verification entirely, and a supplied `user_id` would let them choose their own primary key. |
| Preconditions | `qa.auth.new@textery.test` is unregistered. |
| Test data | Valid body plus `"is_verified": true`, `"user_id": "00000000-0000-4000-8000-000000000000"`, `"created_at": "2000-01-01T00:00:00Z"` |
| Steps | 1. `POST /api/v1/auth/register` with the extra fields.<br>2. Read the response body.<br>3. Read the created row from `users`. |
| Expected result | `201 Created` (undeclared fields are dropped at parse time — no `400`); response `is_verified` is `false`; `user_id` is a server-generated UUID, never `00000000-0000-4000-8000-000000000000`; stored `created_at` is the current time, not `2000-01-01`. |
| Status | Not run |

---

## 2. Register — Happy Path & Re-run Safety

### TC-07-API-2.1 — Valid registration creates a pending account and returns a verification code

| Field | Value |
|---|---|
| Description | The primary contract: a pending account plus the mocked code, which is the only delivery channel there is. |
| Preconditions | `qa.auth.new@textery.test` is unregistered; the injectable clock is pinned to a known instant `T`. |
| Test data | `{"email": "qa.auth.new@textery.test", "password": "Qa!Auth2026", "confirm_password": "Qa!Auth2026"}` |
| Steps | 1. `POST /api/v1/auth/register` with that body.<br>2. Read `verification_code`, `code_expires_at`, `is_verified` from the response.<br>3. Read `is_verified` from the created `users` row. |
| Expected result | `201 Created`; `is_verified` is the JSON boolean `false` and the stored row agrees; `verification_code` is a JSON **string** matching `^[0-9]{6}$`; `code_expires_at` equals `T + 10 minutes`. |
| Status | Not run |

### TC-07-API-2.2 — Duplicate email is rejected, verified or pending

| Field | Value |
|---|---|
| Description | Both account states must refuse a second registration — re-registering a pending account would otherwise be a way around the 60-second resend cooldown. |
| Preconditions | Account V exists and is verified; account P exists and is still pending. |
| Test data | Register attempts for `qa.auth.verified@textery.test` and for `qa.auth.pending@textery.test`, password `Qa!Auth2026` |
| Steps | 1. `POST /api/v1/auth/register` for account V's email.<br>2. `POST /api/v1/auth/register` for account P's email.<br>3. Count `users` rows for each email. |
| Expected result | Both answer `409 Conflict` with `{"error_code": "EMAIL_ALREADY_REGISTERED", "message": "An account with this email address already exists."}`; each email still has exactly one row. |
| Status | Not run |

### TC-07-API-2.3 — Case-folded email uniqueness

| Field | Value |
|---|---|
| Description | Without lowercasing before the uniqueness check, `User@…` and `user@…` become two accounts for one human. |
| Preconditions | An account exists for `user@example.ru`. |
| Test data | Registration for `User@Example.ru`, password `Qa!Auth2026` |
| Steps | 1. `POST /api/v1/auth/register` for `User@Example.ru`.<br>2. Count `users` rows whose email lowercases to `user@example.ru`. |
| Expected result | `409 Conflict` with `error_code` `EMAIL_ALREADY_REGISTERED`; step 2 returns exactly one row, whose stored `email` is the lowercase `user@example.ru`. |
| Status | Not run |

### TC-07-API-2.4 — A retried identical registration request produces exactly one account

| Field | Value |
|---|---|
| Description | A client that retries after a timeout must not end up with a second account or a second live code. |
| Preconditions | A registration for `qa.auth.new@textery.test` has already returned `201`. |
| Test data | The byte-identical request body from that first call |
| Steps | 1. Re-send the identical `POST /api/v1/auth/register`.<br>2. Count `users` rows for the email.<br>3. Count active (unexpired, uninvalidated) verification codes for that account. |
| Expected result | The retry answers `409 EMAIL_ALREADY_REGISTERED`; step 2 returns exactly `1`; step 3 returns exactly `1`. |
| Status | Not run |

### TC-07-API-2.4a — Concurrent registration for the same brand-new email creates exactly one account

| Field | Value |
|---|---|
| Description | Two requests can both pass the uniqueness SELECT before either INSERT lands; only a DB-level unique constraint stops the second row. |
| Preconditions | `qa.auth.race@textery.test` has never been registered. |
| Test data | Two identical register bodies for `qa.auth.race@textery.test`, fired via `asyncio.gather` |
| Steps | 1. Fire both requests at the same instant.<br>2. Record both status codes.<br>3. Count `users` rows for the email. |
| Expected result | Exactly one `201 Created` and one `409 EMAIL_ALREADY_REGISTERED`; never two `201`s and never a `500` from a raw constraint violation; step 3 returns exactly `1`. |
| Status | Not run |

### TC-07-API-2.4b — Case-fold uniqueness is locale-invariant

| Field | Value |
|---|---|
| Description | The Turkish locale lowercases `I` to `ı`, so a locale-sensitive fold produces a different key and lets a duplicate through on one instance but not another. |
| Preconditions | An account exists for `user@example.ru`; the backend process is restarted with `LANG=tr_TR.UTF-8`. |
| Test data | Registration for `User@Example.ru` under the Turkish locale |
| Steps | 1. Restart the backend with `LANG=tr_TR.UTF-8`.<br>2. `POST /api/v1/auth/register` for `User@Example.ru`.<br>3. Repeat the same call under the default locale and compare. |
| Expected result | `409 Conflict EMAIL_ALREADY_REGISTERED` under both locales; the stored folded value is byte-identical in both runs. |
| Status | Not run |

### TC-07-API-2.4c — Unicode-normalization uniqueness for email

| Field | Value |
|---|---|
| Description | Two byte-different but visually identical addresses must not become two accounts the user cannot tell apart. |
| Preconditions | An account exists for `josé@example.ru` in NFC form (`é` = U+00E9). |
| Test data | Registration for `josé@example.ru` (NFD: `e` + U+0301), password `Qa!Auth2026` |
| Steps | 1. `POST /api/v1/auth/register` with the NFD form.<br>2. Count `users` rows matching either form. |
| Expected result | `409 Conflict EMAIL_ALREADY_REGISTERED`; step 2 returns exactly one row in total. |
| Status | Not run |

### TC-07-API-2.4d — Password length limit is measured in code points, not bytes

| Field | Value |
|---|---|
| Description | A byte-length check rejects a legitimate 128-character Cyrillic password at roughly 64 characters. |
| Preconditions | Two unregistered emails are available. |
| Test data | Password `Пароль1!` + `ж` × 120 (exactly 128 code points, 248 UTF-8 bytes), and the same extended by one `ж` (129 code points) |
| Steps | 1. `POST /api/v1/auth/register` with the 128-code-point password.<br>2. Repeat, on the second email, with the 129-code-point password. |
| Expected result | Step 1 answers `201 Created`; step 2 answers `400` with `error_code` `INVALID_PASSWORD`. |
| Status | Not run |

### TC-07-API-2.5 — Registration writes the account and the verification code atomically

| Field | Value |
|---|---|
| Description | An account row with no code is unverifiable and un-re-registerable — the user is locked out of an address they own. |
| Preconditions | The verification-code repository is stubbed to raise after the account INSERT and before commit. |
| Test data | Registration for `qa.auth.atomic@textery.test`, password `Qa!Auth2026` |
| Steps | 1. Arm the code-write failure.<br>2. `POST /api/v1/auth/register`.<br>3. Count `users` rows for that email. |
| Expected result | `500` with the generic `INTERNAL_ERROR` body; step 3 returns zero rows — no account is left behind without a code. |
| Status | Not run |

### TC-07-API-2.6 — Verification code round-trips with leading zeros preserved

| Field | Value |
|---|---|
| Description | Storing or serialising the code as an integer silently turns `042917` into `42917`, and verification then fails for one user in ten. |
| Preconditions | The code generator is seeded to produce a leading-zero code. |
| Test data | Code `042917`, account `qa.auth.new@textery.test` |
| Steps | 1. `POST /api/v1/auth/register` and read `verification_code` from the raw JSON text.<br>2. `POST /api/v1/auth/verify` with that exact string. |
| Expected result | The raw JSON contains `"verification_code": "042917"` — quoted, exactly 6 characters, leading zero intact; step 2 answers `200 OK` with `{"is_verified": true}`. |
| Status | Not run |

### TC-07-API-2.7 — Password is NFC-normalized before hashing

| Field | Value |
|---|---|
| Description | Different keyboards emit the same accented character in different forms; hashing raw bytes makes login depend on which keyboard was used. |
| Preconditions | `qa.auth.nfc@textery.test` is unregistered. |
| Test data | Register password `Café!2026` (NFD); login password `Café!2026` (NFC, U+00E9) |
| Steps | 1. Register with the NFD password.<br>2. Verify the account with the returned code.<br>3. `POST /api/v1/auth/login` with the NFC password. |
| Expected result | Step 1 answers `201`; step 3 answers `200 OK` with a token pair — the two representations hash to the same value. |
| Status | Not run |

---

## 3. Verify Code

### TC-07-API-3.1 — Correct code activates the account

| Field | Value |
|---|---|
| Description | The one transition the whole flow exists for. |
| Preconditions | Account P is pending with an active, unexpired code. |
| Test data | `{"email": "qa.auth.pending@textery.test", "code": "<code from register>"}` |
| Steps | 1. `POST /api/v1/auth/verify` with that body.<br>2. Read `is_verified` from the `users` row. |
| Expected result | `200 OK`, body `{"is_verified": true}`; the stored `is_verified` is `true`. |
| Status | Not run |

### TC-07-API-3.2 — Incorrect code is rejected

| Field | Value |
|---|---|
| Description | A wrong code must neither activate the account nor reveal whether the email exists. |
| Preconditions | Account P is pending with an active code that is not `000000`. |
| Test data | `{"email": "qa.auth.pending@textery.test", "code": "000000"}` |
| Steps | 1. `POST /api/v1/auth/verify` with the wrong code.<br>2. Read `is_verified` from the row. |
| Expected result | `400 Bad Request`, body `{"error_code": "INVALID_OR_EXPIRED_CODE", "message": "The verification code is invalid or has expired."}`; `is_verified` stays `false`. |
| Status | Not run |

### TC-07-API-3.3 — Expired code is rejected, exact boundary enforced

| Field | Value |
|---|---|
| Description | The TTL boundary must be closed at exactly 10 minutes — one second either side decides whether an observed code is still usable. |
| Preconditions | Account P is pending; the injectable clock can be pinned. |
| Test data | Code issued at `T`; clock pinned to `T + 10:00`, then to `T + 09:59` |
| Steps | 1. Pin the clock to `T + 10 minutes` exactly and `POST /api/v1/auth/verify` with the code.<br>2. Re-seed the same state, pin the clock to `T + 9 minutes 59 seconds`, and repeat. |
| Expected result | Step 1 answers `400 INVALID_OR_EXPIRED_CODE` and leaves `is_verified` `false`; step 2 answers `200 OK` with `{"is_verified": true}`. |
| Status | Not run |

### TC-07-API-3.4 — Re-submitting an already-consumed code is idempotent

| Field | Value |
|---|---|
| Description | A retrying client must see the same success, not a conflict — and must not drive a second state transition. |
| Preconditions | The code has been submitted once and the account is now verified. |
| Test data | The same `{"email", "code"}` body as the first call |
| Steps | 1. `POST /api/v1/auth/verify` a second time with the identical body.<br>2. Compare the two responses.<br>3. Inspect the account's verified-at timestamp. |
| Expected result | The second call answers `200 OK` `{"is_verified": true}`, identical to the first and never `409`; the verified-at timestamp is unchanged, so no duplicate transition occurred. |
| Status | Not run |

### TC-07-API-3.5 — Verify against an already-verified account is rejected

| Field | Value |
|---|---|
| Description | Once verified, a non-matching code is a genuine conflict rather than the generic state-hiding rejection. |
| Preconditions | Account V is verified. |
| Test data | `{"email": "qa.auth.verified@textery.test", "code": "123456"}` (any code other than the one that verified it) |
| Steps | 1. `POST /api/v1/auth/verify` with that body. |
| Expected result | `409 Conflict`, body `{"error_code": "ALREADY_VERIFIED", "message": "The account is already verified."}`. |
| Status | Not run |

### TC-07-API-3.6 — Concurrent verify requests for the same account produce exactly one transition

| Field | Value |
|---|---|
| Description | Two in-flight verifies must not both write the transition — a duplicate double-fires any downstream side effect and races the audit record. |
| Preconditions | Account P is pending with an active, correct code. |
| Test data | Two identical verify bodies fired via `asyncio.gather` |
| Steps | 1. Fire both requests at the same instant.<br>2. Record both statuses.<br>3. Count verification transitions recorded for the account. |
| Expected result | Both answer `200 OK` `{"is_verified": true}` — neither `409` nor `500`; step 3 counts exactly one transition. |
| Status | Not run |

---

## 4. Resend Code

### TC-07-API-4.1 — Resend issues a new code and invalidates the previous one

| Field | Value |
|---|---|
| Description | Single active code per account: a stale code still accepted after a resend lets anyone who saw the old one verify. |
| Preconditions | Account P is pending; its current code was issued more than 60 seconds ago. |
| Test data | `{"email": "qa.auth.pending@textery.test"}`; old code `OLD`, new code `NEW` |
| Steps | 1. `POST /api/v1/auth/resend-code`.<br>2. Read `verification_code` from the response.<br>3. `POST /api/v1/auth/verify` with `OLD`.<br>4. `POST /api/v1/auth/verify` with `NEW`. |
| Expected result | Step 1 answers `200 OK` with `verification_code` matching `^[0-9]{6}$`, a fresh `code_expires_at` (issuance + 10 min) and `resend_available_at` 60 s ahead; step 3 answers `400 INVALID_OR_EXPIRED_CODE`; step 4 answers `200 OK` `{"is_verified": true}`. |
| Status | Not run |

### TC-07-API-4.2 — Resend within the cooldown window is rejected

| Field | Value |
|---|---|
| Description | The 60-second cooldown is the only throttle on this endpoint; without it the code channel is unlimited. |
| Preconditions | Account P's code was issued 30 seconds ago (clock pinned). |
| Test data | `{"email": "qa.auth.pending@textery.test"}`, clock at `T + 30s` |
| Steps | 1. `POST /api/v1/auth/resend-code`.<br>2. Count active codes for the account. |
| Expected result | `429 Too Many Requests`, body `{"error_code": "RESEND_COOLDOWN_ACTIVE", "message": "A verification code was recently sent. Please wait before requesting another."}`; step 2 still returns exactly the one pre-existing code. |
| Status | Not run |

### TC-07-API-4.3 — Resend invalidates the old code and issues the new one atomically

| Field | Value |
|---|---|
| Description | If the invalidation commits and the issue does not, the account has zero usable codes and the cooldown blocks the retry — a dead end. |
| Preconditions | The new-code write is stubbed to fail after the old code is invalidated. |
| Test data | Account P, cooldown already elapsed |
| Steps | 1. Arm the new-code write failure.<br>2. `POST /api/v1/auth/resend-code`.<br>3. Count active codes for the account. |
| Expected result | `500` with the generic `INTERNAL_ERROR` body; step 3 returns exactly `1` active code (the old one, rolled back into validity) — never `0`, never `2`. |
| Status | Not run |

### TC-07-API-4.4 — Concurrent resend requests do not both succeed within the cooldown

| Field | Value |
|---|---|
| Description | A read-modify-write cooldown check lets two simultaneous requests both see "eligible" and issue two codes, one of which is immediately dead. |
| Preconditions | Account P is pending and eligible for resend. |
| Test data | Two identical resend bodies fired via `asyncio.gather` |
| Steps | 1. Fire both requests at the same instant.<br>2. Record both statuses.<br>3. Count active codes. |
| Expected result | Exactly one `200 OK` and one `429 RESEND_COOLDOWN_ACTIVE`; step 3 returns exactly `1` active code. |
| Status | Not run |

### TC-07-API-4.5 — Resend against an already-verified account is rejected

| Field | Value |
|---|---|
| Description | A verified account has nothing left to verify; issuing a code for it creates a live credential with no purpose. |
| Preconditions | Account V is verified. |
| Test data | `{"email": "qa.auth.verified@textery.test"}` |
| Steps | 1. `POST /api/v1/auth/resend-code`.<br>2. Count codes issued for the account. |
| Expected result | `409 Conflict`, body `{"error_code": "ALREADY_VERIFIED", "message": "The account is already verified."}` — never `429`; step 2 shows no new code was issued. |
| Status | Not run |

---

## 5. Login — Validation & Access Control

### TC-07-API-5.1 — Login rejected while account is unverified

| Field | Value |
|---|---|
| Description | Verification is the gate; a correct password must not bypass it, and the user needs a distinct message telling them to go verify. |
| Preconditions | Account P is pending with the correct password on file. |
| Test data | `{"email": "qa.auth.pending@textery.test", "password": "Qa!Auth2026"}` |
| Steps | 1. `POST /api/v1/auth/login` with the correct credentials.<br>2. Inspect the response body for any token field. |
| Expected result | `403 Forbidden`, body `{"error_code": "UNVERIFIED", "message": "This account has not been verified yet. Please confirm the code sent to your email."}`; no `access_token` and no `refresh_token` in the body. |
| Status | Not run |

### TC-07-API-5.2 — Invalid credentials return a single generic error

| Field | Value |
|---|---|
| Description | Different answers for "no such email" and "wrong password" turn the login form into an account-existence oracle. |
| Preconditions | Account V is verified; `qa.auth.ghost@textery.test` has no account. |
| Test data | Unknown email + `Qa!Auth2026`; account V's email + `WrongPass1!` |
| Steps | 1. `POST /api/v1/auth/login` for the unknown email.<br>2. `POST /api/v1/auth/login` for account V with the wrong password.<br>3. Compare the two responses field by field. |
| Expected result | Both answer `401 Unauthorized` with byte-identical bodies `{"error_code": "INVALID_CREDENTIALS", "message": "The email address or password is incorrect."}`; no token in either. |
| Status | Not run |

### TC-07-API-5.3 — Failed-attempt counter increments atomically across concurrent failures

| Field | Value |
|---|---|
| Description | A load-then-save increment loses one of two simultaneous failures, so an attacker gets more attempts than the threshold allows. |
| Preconditions | Account V is verified with `failed_attempt_count = 0`. |
| Test data | Two wrong-password logins (`WrongPass1!`) for account V, fired via `asyncio.gather` |
| Steps | 1. Fire both requests at the same instant.<br>2. Read `failed_attempt_count` from the account row. |
| Expected result | Both answer `401 INVALID_CREDENTIALS`; step 2 returns exactly `2`, never `1`. |
| Status | Not run |

### TC-07-API-5.4 — Account locks out after N consecutive failed attempts

| Field | Value |
|---|---|
| Description | The lockout gate must run before password verification, so even a correct password is refused once the threshold is reached. |
| Preconditions | Account V is verified with `failed_attempt_count = 5` (the threshold). |
| Test data | `{"email": "qa.auth.verified@textery.test", "password": "Qa!Verified2026"}` — the **correct** password |
| Steps | 1. `POST /api/v1/auth/login` with the correct credentials. |
| Expected result | `403 Forbidden`, body `{"error_code": "ACCOUNT_LOCKED", "message": "This account is temporarily locked due to repeated failed logins."}` — distinct from `UNVERIFIED`; no token issued. |
| Status | Not run |

### TC-07-API-5.5 — Lockout auto-expires after the cooldown window

| Field | Value |
|---|---|
| Description | A lockout that never lifts is a permanent denial of service against a legitimate user. |
| Preconditions | Account V is locked out at `T`; the injectable clock can be advanced past the lockout cooldown window `C`. |
| Test data | Correct credentials for account V; clock at `T + C + 1s` |
| Steps | 1. Advance the clock past the cooldown.<br>2. `POST /api/v1/auth/login` with correct credentials.<br>3. Read `failed_attempt_count`. |
| Expected result | `200 OK` with `access_token`, `refresh_token`, `access_token_expires_at`, `refresh_token_expires_at`; step 3 returns `0`. |
| Status | Not run |

### TC-07-API-5.5a — Lockout cooldown boundary is enforced at the exact expiry instant

| Field | Value |
|---|---|
| Description | An off-by-one at the boundary either releases the lock a tick early or holds it a tick too long; the instant itself must still be locked. |
| Preconditions | Account V is locked out at `T`; cooldown window `C`. |
| Test data | Clock pinned to `T + C` exactly, then to `T + C + 1s` |
| Steps | 1. Pin the clock to `T + C` and `POST /api/v1/auth/login` with correct credentials.<br>2. Pin the clock to `T + C + 1s` and repeat. |
| Expected result | Step 1 answers `403 ACCOUNT_LOCKED`; step 2 answers `200 OK` with a token pair. |
| Status | Not run |

### TC-07-API-5.6 — Lockout read failure fails closed

| Field | Value |
|---|---|
| Description | If an unreadable lockout state let the login proceed, an attacker who can stress the DB gets unlimited attempts. |
| Preconditions | The lockout-state read is stubbed to raise or time out. |
| Test data | Correct credentials for account V |
| Steps | 1. Arm the lockout-read failure.<br>2. `POST /api/v1/auth/login` with correct credentials.<br>3. Inspect the response body. |
| Expected result | The login is denied — `500` with the generic `INTERNAL_ERROR` body, never `200`; no `access_token` or `refresh_token` in the body. |
| Status | Not run |

### TC-07-API-5.6a — Verification-flag read failure fails closed

| Field | Value |
|---|---|
| Description | The `is_verified` read is a separate call from the lockout read; guarding one and not the other leaves the second fail-open path live. |
| Preconditions | The `is_verified` read is stubbed to fail independently of the lockout read. |
| Test data | Correct credentials for account V |
| Steps | 1. Arm only the `is_verified`-read failure.<br>2. `POST /api/v1/auth/login` with correct credentials. |
| Expected result | The login is denied — `500` with the generic `INTERNAL_ERROR` body; no token field in the response. |
| Status | Not run |

### TC-07-API-5.7 — Malicious email/password input does not cause a validation hang

| Field | Value |
|---|---|
| Description | Catastrophic backtracking in an email or password regex turns one request into a CPU-pinning denial of service. |
| Preconditions | Backend running normally; the standard configured request timeout applies. |
| Test data | `email` = `a` × 254 + `!` (no `@`, at the maximum allowed length); `password` = `a` × 127 + `!` shaped to force `(a+)+` backtracking |
| Steps | 1. `POST /api/v1/auth/register` with those values and time the call.<br>2. `POST /api/v1/auth/login` with the same values and time the call. |
| Expected result | Each returns well inside the request timeout (under 1 s) with `400`/`401` per the ordinary length/format rules — no hang, no timeout, no worker pinned at 100% CPU. |
| Status | Not run |

---

## 6. Login — Happy Path & Token Refresh

### TC-07-API-6.1 — Valid credentials on a verified account issue a token pair

| Field | Value |
|---|---|
| Description | The success contract, plus the counter reset without which a user who mistyped four times stays one mistake from lockout forever. |
| Preconditions | Account V is verified with `failed_attempt_count = 3`. |
| Test data | `{"email": "qa.auth.verified@textery.test", "password": "Qa!Verified2026"}` |
| Steps | 1. `POST /api/v1/auth/login`.<br>2. Read the four token fields.<br>3. Read `failed_attempt_count` from the row. |
| Expected result | `200 OK` with non-empty `access_token` and `refresh_token` (each a three-segment JWT) plus `access_token_expires_at` and `refresh_token_expires_at` as ISO-8601 instants in the future; step 3 returns `0`. |
| Status | Not run |

### TC-07-API-6.1a — Failed-attempt-counter reset and refresh-token persistence commit as one unit

| Field | Value |
|---|---|
| Description | A reset counter with no persisted refresh token hands the user a token the server will not honour, while also clearing the brute-force defence. |
| Preconditions | Account V is verified with `failed_attempt_count = 3`; the refresh-token persistence write is stubbed to fail after the counter reset. |
| Test data | Correct credentials for account V |
| Steps | 1. Arm the refresh-token write failure.<br>2. `POST /api/v1/auth/login` with correct credentials.<br>3. Read `failed_attempt_count` and the stored refresh tokens. |
| Expected result | Either `200 OK` with a token pair **and** a persisted refresh token, or `500` with the generic `INTERNAL_ERROR` body **and** `failed_attempt_count` still `3` — never a reset counter alongside zero persisted refresh tokens. |
| Status | Not run |

### TC-07-API-6.2 — Refresh returns a new access token for a valid refresh token

| Field | Value |
|---|---|
| Description | The refresh contract: a short-lived access token must be renewable without re-entering the password. |
| Preconditions | A valid, unexpired refresh token from a prior login of account V. |
| Test data | `{"refresh_token": "<refresh_token from login>"}` |
| Steps | 1. `POST /api/v1/auth/refresh` with that body.<br>2. Present the returned `access_token` to the protected endpoint `GET /api/v1/auth/me`. |
| Expected result | `200 OK` with a non-empty `access_token` and an `access_token_expires_at` in the future; step 2 answers `200 OK`. |
| Status | Not run |

### TC-07-API-6.3 — Refresh rejects an expired or invalid refresh token

| Field | Value |
|---|---|
| Description | An expired or forged refresh token must not mint an access token. |
| Preconditions | One expired refresh token is available; one arbitrary string is not a token at all. |
| Test data | The expired token; and `{"refresh_token": "not-a-token"}` |
| Steps | 1. `POST /api/v1/auth/refresh` with the expired token.<br>2. Repeat with `not-a-token`. |
| Expected result | Both answer `401 Unauthorized` with `{"error_code": "INVALID_REFRESH_TOKEN", "message": "The refresh token is invalid or has expired."}`; no `access_token` in either body. |
| Status | Not run |

### TC-07-API-6.4 — Refresh rejects a token whose claim shape no longer matches current code

| Field | Value |
|---|---|
| Description | Refresh tokens live 7–30 days, so a claim renamed mid-life arrives at code that no longer expects it — a `KeyError` there is a `500`, not a `401`. |
| Preconditions | A refresh token is minted with the previous claim set (one claim renamed, one dropped, one extra added), signed with the current key. |
| Test data | Token carrying claims `{sub, exp, typ}` where current code expects `{user_id, exp, token_type}` |
| Steps | 1. `POST /api/v1/auth/refresh` with that token.<br>2. Read the server log for the request. |
| Expected result | `401 Unauthorized` with `{"error_code": "INVALID_REFRESH_TOKEN", ...}`; never `500`; the log carries no unhandled `KeyError` or deserialization traceback. |
| Status | Not run |

### TC-07-API-6.5 — Access token is valid up to, not past, its exact expiry instant

| Field | Value |
|---|---|
| Description | The expiry boundary decides how long a leaked access token stays usable; an inclusive comparison the wrong way extends it. |
| Preconditions | An access token for account V with expiry instant `E`; the clock is injectable. |
| Test data | Clock pinned to `E − 1s`, then to `E + 1s`; protected endpoint `GET /api/v1/auth/me` |
| Steps | 1. Pin the clock to `E − 1s` and call the protected endpoint with the token.<br>2. Pin the clock to `E + 1s` and repeat. |
| Expected result | Step 1 answers `200 OK`; step 2 answers `401 Unauthorized` with `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}`. |
| Status | Not run |
