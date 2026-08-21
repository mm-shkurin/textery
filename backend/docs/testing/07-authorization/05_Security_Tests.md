<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Authorization — Security Tests

Scenarios scoped to this story's actual attack surface: password storage, JWT issuance,
brute-force/rate-limit abuse, input injection via the email field, mass assignment on
registration, and the resend/verify credential-disclosure trade-off. Generic 401
(unauthenticated), CORS, and security-header checks are cross-cutting and out of scope
here.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account P (pending) | `qa.sec.pending@textery.test` / `Qa!Sec2026` |
| Account V (verified) | `qa.sec.verified@textery.test` / `Qa!SecVerified2026` |
| Sentinel password | `Sentinel!Passw0rd-4f19` |
| Sentinel verification code | `042917` |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic client-safe text>"}` |
| Log capture | the backend container's stdout plus any persisted structured-log file, for the duration of the case |
| Lockout threshold / resend cooldown | 5 consecutive failures / 60 seconds |

---

## TC-07-SEC-1 — Password Hashing

| Field | Value |
|---|---|
| Description | A plaintext or reversibly-encoded password column turns one database read into every user's credentials on every other site they reuse it on. |
| Preconditions | Log capture running; `qa.sec.new@textery.test` is unregistered. |
| Test data | Registration password `Sentinel!Passw0rd-4f19` |
| Steps | 1. `POST /api/v1/auth/register` with that password.<br>2. `SELECT password_hash FROM users WHERE email = 'qa.sec.new@textery.test'`.<br>3. Grep the response body and the captured logs for the sentinel. |
| Expected result | The stored value starts with a bcrypt prefix (`$2a$`/`$2b$`/`$2y$`) followed by a cost factor and a 53-character salt+digest, and is never equal to the plaintext; the literal `Sentinel!Passw0rd-4f19` appears in zero response bodies and zero log lines. |
| Status | Not run |

## TC-07-SEC-2 — Verification Code Never Logged Beyond the Mocked Response

| Field | Value |
|---|---|
| Description | The code is a live credential regardless of being "mocked" — a copy in a persisted log line is a copy an operator or a log shipper can replay. |
| Preconditions | Log capture running; account P pending with resend cooldown elapsed. |
| Test data | The 6-digit code returned by register and by resend-code |
| Steps | 1. `POST /api/v1/auth/register` and record the returned code.<br>2. `POST /api/v1/auth/resend-code` and record the new code.<br>3. Grep the captured stdout and structured-log output for both codes. |
| Expected result | Each code appears exactly once — in its own API response body — and zero times in the captured log output, at any level, including DEBUG. |
| Status | Not run |

## TC-07-SEC-3 — Mass Assignment on Registration

| Field | Value |
|---|---|
| Description | A bound `is_verified: true` skips the whole verification flow; a bound `user_id` lets the attacker pick a primary key and collide with someone else's row. |
| Preconditions | `qa.sec.mass@textery.test` is unregistered. |
| Test data | Valid body plus `"is_verified": true`, `"user_id": "00000000-0000-4000-8000-000000000000"`, `"created_at": "2000-01-01T00:00:00Z"` |
| Steps | 1. `POST /api/v1/auth/register` with the extra fields.<br>2. Read the created row from `users`. |
| Expected result | `201 Created` with `is_verified` `false`; the stored `id` is a freshly generated UUID, never `00000000-0000-4000-8000-000000000000`; the stored `created_at` is the current time, not `2000-01-01T00:00:00Z`. |
| Status | Not run |

## TC-07-SEC-4 — SQL Injection via Email Field

| Field | Value |
|---|---|
| Description | The email field reaches a `WHERE email = …` lookup on four endpoints; a concatenated query there is a full-table read or a dropped table. |
| Preconditions | The `users` table exists and holds at least the two seed accounts. |
| Test data | `' OR '1'='1`, `admin@textery.test'--`, `x@y.z'; DROP TABLE users;--`, `' UNION SELECT password_hash FROM users--` |
| Steps | 1. Send each payload as `email` to register, verify, resend-code and login in turn.<br>2. After each call, `SELECT count(*) FROM users`.<br>3. Read each response body. |
| Expected result | Every call answers the ordinary rejection for an invalid or unknown email (`400 INVALID_EMAIL`, or `401 INVALID_CREDENTIALS` on login) — never `200`, never a `500` with a driver message; the row count in step 2 is unchanged after every payload and the `users` table still exists; no response body contains a `password_hash` value. |
| Status | Not run |

## TC-07-SEC-5 — Log Injection via Email Field

| Field | Value |
|---|---|
| Description | Embedded CR/LF in a logged field lets an attacker forge whole log records — including a fake "login succeeded" line — and corrupt any downstream log parser. |
| Preconditions | Log capture running; structured logging enabled. |
| Test data | `email` = `victim@textery.test\r\nINFO auth: login succeeded for admin@textery.test` (literal CR and LF) |
| Steps | 1. `POST /api/v1/auth/register` with that email.<br>2. Read the captured log output for the request.<br>3. Parse the captured output line by line as JSON. |
| Expected result | The request answers `400 INVALID_EMAIL`; the payload occupies exactly one log record with the CR/LF escaped (`\r\n`) or stripped inside the field value; no forged `login succeeded` record appears as a separate line, and every captured line still parses as valid JSON. |
| Status | Not run |

## TC-07-SEC-6 — Rate Limiting — Login Brute Force

| Field | Value |
|---|---|
| Description | Without a lockout, an offline-strength guessing attack runs online at whatever rate the endpoint answers. |
| Preconditions | Account V is verified with `failed_attempt_count = 0`. |
| Test data | 5 logins with `WrongPass1!`, then one login with the correct `Qa!SecVerified2026` |
| Steps | 1. Submit five consecutive wrong-password logins for account V.<br>2. Submit a sixth login with the **correct** password.<br>3. Advance the injectable clock past the lockout cooldown and retry with the correct password. |
| Expected result | Steps 1's five calls answer `401 INVALID_CREDENTIALS`; step 2 answers `403` with `{"error_code": "ACCOUNT_LOCKED", "message": "This account is temporarily locked due to repeated failed logins."}` despite the correct password, and issues no token; step 3 answers `200 OK` with a token pair. |
| Status | Not run |

## TC-07-SEC-7 — Rate Limiting — Resend-Code Abuse

| Field | Value |
|---|---|
| Description | The 60-second cooldown is the only throttle on the endpoint that hands out live verification codes. |
| Preconditions | A resend for account P has just succeeded at instant `T`. |
| Test data | Second resend at `T + 30s`, third at `T + 61s` |
| Steps | 1. `POST /api/v1/auth/resend-code` at `T + 30s`.<br>2. Count active codes for the account.<br>3. Repeat the call at `T + 61s`. |
| Expected result | Step 1 answers `429` with `{"error_code": "RESEND_COOLDOWN_ACTIVE", "message": "A verification code was recently sent. Please wait before requesting another."}` and issues no code; step 2 returns exactly `1`; step 3 answers `200 OK` with a new code. |
| Status | Not run |

## TC-07-SEC-8 — JWT — Algorithm and Expiry Enforcement

| Field | Value |
|---|---|
| Description | Trusting the token's own `alg` header lets anyone mint an admin token with `"alg": "none"`; ignoring `exp` makes every leaked token permanent. |
| Preconditions | A valid access token for account V is available as a template; protected endpoint `GET /api/v1/auth/me`. |
| Test data | Token A: header `{"alg": "none", "typ": "JWT"}`, unchanged claims, empty signature. Token B: header `{"alg": "HS256"}` re-signed with the attacker's own key. Token C: the genuine token with `exp` set one hour in the past. |
| Steps | 1. Present token A to `GET /api/v1/auth/me`.<br>2. Present token B.<br>3. Present token C. |
| Expected result | All three answer `401 Unauthorized` with `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}`; none answers `200`; none produces a `500` or a stack trace. |
| Status | Not run |

## TC-07-SEC-9 — Refresh Token Rejected After Signing-Key Rotation

| Field | Value |
|---|---|
| Description | Refresh tokens outlive a key rotation by design; a verification failure that escapes as an exception turns every rotation into a wave of `500`s. |
| Preconditions | A valid refresh token was issued under key `K1`; the backend is restarted with the JWT secret set to `K2`. |
| Test data | The `K1`-signed refresh token; new secret `K2` set in the env file |
| Steps | 1. Log in as account V and keep the refresh token.<br>2. Rotate the JWT secret to `K2` and restart the backend.<br>3. `POST /api/v1/auth/refresh` with the `K1` token.<br>4. Read the server log for that request. |
| Expected result | `401 Unauthorized` with `{"error_code": "INVALID_REFRESH_TOKEN", "message": "The refresh token is invalid or has expired."}` — never `500`; the log holds no unhandled signature-verification traceback. |
| Status | Not run |

## TC-07-SEC-10 — Resend/Verify Credential Disclosure — Documented, Rate-Limited Exposure

| Field | Value |
|---|---|
| Description | Documents the accepted trade-off of the mocked-email design rather than asserting it is safe: resend-code takes a raw email, not a session, so knowing an address yields a live code. The test pins the exposure's exact shape and its only throttle, so a future production rollout cannot inherit it unnoticed. |
| Preconditions | Account P exists and is pending; the caller is unauthenticated and does not know the password. |
| Test data | `{"email": "qa.sec.pending@textery.test"}`, no `Authorization` header |
| Steps | 1. `POST /api/v1/auth/resend-code` with no credentials of any kind.<br>2. Read `verification_code` from the response.<br>3. `POST /api/v1/auth/verify` with that code for the victim's email.<br>4. Immediately repeat step 1. |
| Expected result | Step 1 answers `200 OK` and returns a live 6-digit code for an account the caller does not own; step 3 verifies that account — the exposure is real and matches `07_Authorization_Notes.md`; step 4 answers `429 RESEND_COOLDOWN_ACTIVE`, confirming the 60-second cooldown is the only friction present. Any change to step 1's outcome (an auth requirement added) must update the notes rather than silently pass. |
| Status | Not run |

## TC-07-SEC-11 — Sentinel Secret Absent From Every Failure Path

| Field | Value |
|---|---|
| Description | Secrets leak on the paths nobody demos — the error paths. Seeding a unique sentinel makes any echo of it, in a body or a log, unmistakable. |
| Preconditions | Account V is seeded with password `Sentinel!Passw0rd-4f19`; account P's code is seeded to `042917`; log capture running. |
| Test data | Six failure paths: wrong password, wrong code, expired code, locked-out login, unverified-account login, invalid refresh token |
| Steps | 1. Trigger each of the six failure paths in turn.<br>2. Grep each response body for `Sentinel!Passw0rd-4f19` and `042917`.<br>3. Grep the captured log output for both sentinels. |
| Expected result | Each path returns its own defined `{error_code, message}` body (`INVALID_CREDENTIALS`, `INVALID_OR_EXPIRED_CODE`, `ACCOUNT_LOCKED`, `UNVERIFIED`, `INVALID_REFRESH_TOKEN`); neither sentinel appears in any of the six bodies, and neither appears anywhere in the captured logs. |
| Status | Not run |

## TC-07-SEC-12 — Fail-Closed Paths Emit a Distinguishable Signal

| Field | Value |
|---|---|
| Description | A fail-closed denial looks to the client exactly like a normal refusal, so without its own server-side signal an outage of the lockout or verification read is invisible until someone reports being unable to log in. |
| Preconditions | The lockout-state read and the `is_verified` read can each be stubbed to fail independently; log/metric capture running. |
| Test data | Correct credentials for account V; a genuine locked-out login and a genuine unverified login as the control cases |
| Steps | 1. Arm the lockout-read failure, attempt login, capture logs and metrics.<br>2. Arm only the `is_verified`-read failure, attempt login, capture again.<br>3. Run a genuine `403 ACCOUNT_LOCKED` login and a genuine `403 UNVERIFIED` login as controls, capturing each. |
| Expected result | Steps 1 and 2 each emit exactly one error-level record (or metric increment) identifying which read failed, and the two identifiers differ from each other; neither identifier is emitted by either control run in step 3. |
| Status | Not run |
