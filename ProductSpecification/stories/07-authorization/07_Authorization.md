# Authorization (email + password, mocked verification code)

## Brief Description

Users register with email + password, verify their email via a mocked 6-digit code
returned in the API response, then log in to receive a JWT access + refresh token pair.

## Flow

1. User submits email + password to `POST /auth/register`.
2. Backend validates password policy and email uniqueness, hashes the password, creates
   a `User` with `is_verified=false`, generates a 6-digit code (TTL 10 min), returns the
   code in the response body.
3. User submits the code to `POST /auth/verify` (email + code).
4. Backend validates the code (matches, not expired), sets `is_verified=true`.
5. If code is wrong/expired, user may call `POST /auth/resend-code` (max 1 per 60s) to
   get a new code.
6. User submits email + password to `POST /auth/login`.
7. Backend checks `is_verified=true`, verifies password hash, checks lockout counter.
8. On success: issues JWT access token + refresh token, resets failed-attempt counter.
9. On failure: increments failed-attempt counter; after N consecutive failures, account
   is locked out for a cooldown window.
10. User calls `POST /auth/refresh` with a valid refresh token to get a new access token.

## Acceptance Criteria

- Registration rejects weak passwords, duplicate emails, and malformed email addresses.
- Registration response includes the mocked verification code (no email is sent).
- Login is rejected with a clear error while the account is unverified.
- Verify-code endpoint rejects expired or incorrect codes.
- Resend-code is rejected if called again within 60 seconds of the previous issuance.
- Login is rejected with a clear error while the account is unverified.
- Login is locked out after N consecutive failed password attempts, with a clear error.
- Successful login returns a valid JWT access token and refresh token.
- Refresh endpoint returns a new valid access token given a valid, unexpired refresh
  token; rejects expired or invalid refresh tokens.
- Rate-limit and lockout state persist in the database (not in-process memory), and are
  updated via atomic operations so concurrent requests across multiple backend instances
  never lose an increment or double-issue a code.
- Re-submitting the same verify code twice, or re-submitting an identical registration
  request twice, produces exactly one state transition / one `User` row — not a silent
  double-effect or an inconsistent error.
- Registration's `User` row + verification-code write commit atomically (both or
  neither); resend-code's invalidate-old + issue-new writes commit atomically.
- Illegal transitions are rejected with a defined error: verify on an already-verified
  account, resend after verification, login while locked out.
- Client-supplied fields outside `email`/`password` (e.g. `is_verified`, `id`) in the
  registration body are ignored, never bound onto the created user.
- A failure/timeout while reading lockout or verification state fails closed (login
  denied), never fails open.
- Password, verification code, and JWT secret never appear in any API response body or
  persisted log line, across every success and failure path (including unexpected
  errors — no stack traces/internal ids leak to the client).
- Protected routes/endpoints reject requests with a missing, expired, or tampered access
  token at the server, independent of any client-side route guard.

## Validation Rules

| Field | Rule |
|-------|------|
| email | valid format, max 255 chars, case-folded (lowercased) before uniqueness check/storage, unique across all accounts (verified or pending) |
| password | min 8 chars, max 128 chars, ≥1 digit, ≥1 uppercase, ≥1 lowercase, ≥1 special char, NFC-normalized before hashing |
| verification code | 6-digit string (zero-padded, never stored/compared as integer), TTL 10 minutes, single active code per account, exact-expiry-instant treated as expired |
| resend-code | max 1 request per 60 seconds per account; invalidates prior code atomically with issuing the new one |
| login attempts | lock out after N consecutive failures (N decided at api-spec time); auto-unlocks after cooldown window; failed/attempt and resend-cooldown counters updated via atomic DB operations (conditional update / atomic increment, not read-modify-write) to stay correct across concurrent requests and multiple backend instances |

## Screen States

- Registration form (email, password, confirm password)
- Verification-code entry screen (6-digit input, resend action)
- Login form (email, password)
- Account-locked error state
- Authenticated app shell (token stored, protected routes accessible)

## Core Requirements

- `User` domain entity: email (case-folded), password hash, `is_verified`, timestamps.
- Verification-code value object/entity: 6-digit string code, expiry, associated
  account; stored/compared as a string, never an integer.
- Login lockout/rate-limit state persisted in DB, keyed per account, updated via atomic
  DB operations — never in-process, never plain read-modify-write.
- JWT signing secret sourced from `infra/.env`, never hardcoded. Refresh-token
  validation must handle a signing-key rotation or claim-shape change made after the
  token was issued (given 7-30 day TTL) by rejecting cleanly, not crashing.
- Password never logged or returned in any API response; NFC-normalized before hashing.
- Injectable/mockable clock for all TTL and cooldown logic (code expiry, resend
  cooldown, lockout cooldown), so tests can pin exact boundary instants.
- `email` value sanitized/parameterized at every sink (DB query, log line, error
  response) — no log-forging or injection via crafted email input.
- Frontend: in-flight submit buttons (register/verify/resend/login) disabled to prevent
  duplicate-click double-submission; distinct loading/error/network-error states beyond
  the named validation errors; resend-code button shows cooldown countdown, not a
  silently-reclickable control.

Accepted trade-off (see Notes "Security Considerations"): resend-code/verify take a raw
`email`, not an authenticated session — since the mocked code is returned directly in
the response body by design (per product brief), an unauthenticated caller who knows a
target email can retrieve that account's live code. Documented and accepted for this
mock/demo scope; would need a registration-session token if this endpoint shape carries
into a production mail-based flow later.
