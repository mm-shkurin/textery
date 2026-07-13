# Authorization — API Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with registration validation (no infrastructure needed), then registration
> happy path + re-run-safety guards, then verify-code, then resend-code, then login
> (validation, lockout, happy path), then refresh.

No parent-resource prerequisite guards apply to this story (no board/column-style
dependency) — the only "guards" are field-level validation and the re-run-safety
scenarios below (mandatory per the Side-Effect & Idempotency Guard Checklist: the
register→code-issue and resend→invalidate-and-reissue sequences both mutate persisted
state and can be re-run by a retrying client).

---

## 1. Register — Validation

### 1.1 Reject malformed email

```gherkin
Given a registration request with a malformed email address
When the client submits the request
Then the response is a validation error
And no account is created
```

### 1.2 Reject email exceeding the length limit

```gherkin
Given a registration request whose email is 256 characters
When the client submits the request
Then the response is a validation error
And no account is created
```

### 1.3 Reject password failing the policy

```gherkin
Given a registration request whose password is only 7 characters
When the client submits the request
Then the response is a validation error

Given a registration request whose password has no digit
When the client submits the request
Then the response is a validation error

Given a registration request whose password has no uppercase letter
When the client submits the request
Then the response is a validation error

Given a registration request whose password has no special character
When the client submits the request
Then the response is a validation error

Given a registration request whose password exceeds 128 characters
When the client submits the request
Then the response is a validation error
```

### 1.4 Reject password/confirm_password mismatch

```gherkin
Given a registration request whose password and confirm_password differ
When the client submits the request
Then the response is a validation error
And no account is created
```

### 1.5 Ignore server-owned fields in the request body

```gherkin
Given a registration request whose body also sets is_verified to true and an id
When the client submits the request
Then the created account's is_verified is false, not the attacker-supplied value
And the created account's id is server-generated, not the attacker-supplied value
```

---

## 2. Register — Happy Path & Re-run Safety

### 2.1 Valid registration creates a pending account and returns a verification code

```gherkin
Given a registration request with a valid, unused email and a policy-compliant password
When the client submits the request
Then an account is created with is_verified false
And the response includes a 6-digit verification code as a zero-padded string
And the response includes the code's expiry, 10 minutes from issuance
```

### 2.2 Duplicate email is rejected, verified or pending

```gherkin
Given an account already exists for an email, verified
When a registration request is submitted for that same email
Then the response is rejected as a duplicate
And no second account is created

Given an account already exists for an email, still pending verification
When a registration request is submitted for that same email
Then the response is rejected as a duplicate
And no second account is created
```

### 2.3 Case-folded email uniqueness

```gherkin
Given an account already exists for "user@example.ru"
When a registration request is submitted for "User@Example.ru"
Then the response is rejected as a duplicate, the same account
```

### 2.4 A retried identical registration request produces exactly one account

```gherkin
Given a registration request has already succeeded, creating a pending account and a code
When the client retries the identical registration request against the same email
Then exactly one account exists for that email
And exactly one verification code is active for that account
```

### 2.4a Concurrent registration for the same brand-new email creates exactly one account

```gherkin
Given an email has never been registered before
When two registration requests for that exact email are submitted at the same instant
Then exactly one account is created
And the other request is rejected as a duplicate, not a second row racing the uniqueness check
```

### 2.4b Case-fold uniqueness is locale-invariant

```gherkin
Given an account already exists for "user@example.ru"
And the server's runtime locale is forced to a locale with non-standard casing rules (e.g. Turkish)
When a registration request is submitted for "User@Example.ru"
Then the response is still rejected as a duplicate, the same account
And the case-fold does not diverge from the invariant-locale result
```

### 2.4c Unicode-normalization uniqueness for email

```gherkin
Given an account already exists for an email whose local part is a precomposed accented character (NFC form)
When a registration request is submitted for the visually identical email written with a combining-character sequence (NFD form)
Then the response is rejected as a duplicate, the same account
```

### 2.4d Password length limit is measured in code points, not bytes

```gherkin
Given a registration password built from multibyte Unicode characters totalling exactly 128 code points
When the client submits the request
Then the request is accepted

Given the same password extended to 129 code points
When the client submits the request
Then the response is a validation error
```

### 2.5 Registration writes the account and the verification code atomically

```gherkin
Given the verification-code write would fail after the account row is written
When a registration request is submitted
Then no account row is left behind without an associated verification code
```

### 2.6 Verification code round-trips with leading zeros preserved

```gherkin
Given a registration produces a verification code with a leading zero, e.g. "042917"
When the code is read back from the registration response and resubmitted to verify
Then the code matches digit-for-digit, exactly 6 characters, no leading zero lost
```

### 2.7 Password is NFC-normalized before hashing

```gherkin
Given a registration password containing a combining-character sequence for an accented letter
And a later login attempt supplies the same visual password as a single precomposed character
When both requests are processed
Then the login succeeds, the two representations are treated as the same password
```

---

## 3. Verify Code

### 3.1 Correct code activates the account

```gherkin
Given a pending account with an active, unexpired verification code
When the client submits that code for that email
Then the account becomes verified
```

### 3.2 Incorrect code is rejected

```gherkin
Given a pending account with an active verification code
When the client submits a code that does not match
Then the response is a validation error
And the account remains unverified
```

### 3.3 Expired code is rejected, exact boundary enforced

```gherkin
Given a pending account whose verification code was issued exactly 10 minutes ago
When the client submits that code
Then the response is a validation error, the code is expired

Given a pending account whose verification code was issued 9 minutes 59 seconds ago
When the client submits that code
Then the code is accepted, not yet expired
```

### 3.4 Re-submitting an already-consumed code is idempotent

```gherkin
Given a code has already been submitted once and the account is now verified
When the client submits that same code again
Then the response is the same success outcome
And no duplicate state transition occurs
```

### 3.5 Verify against an already-verified account is rejected

```gherkin
Given an account is already verified
When the client submits a verify request for that account, any code
Then the response is rejected, already verified
```

### 3.6 Concurrent verify requests for the same account produce exactly one transition

```gherkin
Given a pending account with an active, correct verification code
When two verify requests with that code are submitted at the same instant
Then exactly one request transitions the account to verified
And the other observes the resulting verified state, not a duplicate transition or an error
```

---

## 4. Resend Code

### 4.1 Resend issues a new code and invalidates the previous one

```gherkin
Given a pending account with an active verification code
When the client requests a resend, more than 60 seconds after the previous issuance
Then a new 6-digit code is returned
And the previous code no longer verifies the account
```

### 4.2 Resend within the cooldown window is rejected

```gherkin
Given a pending account whose verification code was issued 30 seconds ago
When the client requests a resend
Then the response is rejected, cooldown active
And no new code is issued
```

### 4.3 Resend invalidates the old code and issues the new one atomically

```gherkin
Given the new-code write would fail after the old code is invalidated
When a resend request is submitted
Then the account is left with exactly one active code, old or new, never zero
```

### 4.4 Concurrent resend requests do not both succeed within the cooldown

```gherkin
Given a pending account eligible for resend
When two resend requests are submitted for that account at the same instant
Then exactly one request succeeds and issues a new code
And the other is rejected, cooldown active
```

### 4.5 Resend against an already-verified account is rejected

```gherkin
Given an account is already verified
When the client requests a resend for that account
Then the response is rejected, already verified
```

---

## 5. Login — Validation & Access Control

### 5.1 Login rejected while account is unverified

```gherkin
Given a pending, unverified account with a correct password on file
When the client submits a login request with correct credentials
Then the response is rejected, account not verified
And no token is issued
```

### 5.2 Invalid credentials return a single generic error

```gherkin
Given no account exists for an email
When the client submits a login request for that email
Then the response is rejected with a generic invalid-credentials error

Given a verified account exists but the submitted password is wrong
When the client submits the login request
Then the response is rejected with the same generic invalid-credentials error
```

### 5.3 Failed-attempt counter increments atomically across concurrent failures

```gherkin
Given a verified account with zero recorded failed attempts
When two login requests with wrong passwords are submitted for that account at the same instant
Then the failed-attempt counter reflects both failures, not one lost to a race
```

### 5.4 Account locks out after N consecutive failed attempts

```gherkin
Given a verified account has just reached N consecutive failed login attempts
When the client submits another login request, even with the correct password
Then the response is rejected, account locked out
```

### 5.5 Lockout auto-expires after the cooldown window

```gherkin
Given an account is locked out and the lockout cooldown window has elapsed
When the client submits a login request with correct credentials
Then the login succeeds, the lockout no longer applies
```

### 5.5a Lockout cooldown boundary is enforced at the exact expiry instant

```gherkin
Given an account is locked out and exactly at the lockout cooldown's expiry instant
When the client submits a login request with correct credentials
Then the login is still rejected, locked out

Given the same account one tick after the cooldown's expiry instant
When the client submits a login request with correct credentials
Then the login succeeds
```

### 5.6 Lockout read failure fails closed

```gherkin
Given the lockout-state read would fail or time out during a login attempt
When the client submits a login request
Then the login is denied
And no token is issued
```

### 5.6a Verification-flag read failure fails closed

```gherkin
Given the is_verified-state read would fail or time out during a login attempt, independent of the lockout-state read
When the client submits a login request with correct credentials
Then the login is denied
And no token is issued
```

### 5.7 Malicious email/password input does not cause a validation hang

```gherkin
Given an email or password value crafted to trigger catastrophic backtracking in a naive validation regex, at the maximum allowed length
When the client submits a registration or login request with that value
Then validation completes within the standard request timeout
And the request is rejected or accepted per the ordinary length/format rules, not hung
```

---

## 6. Login — Happy Path & Token Refresh

### 6.1 Valid credentials on a verified account issue a token pair

```gherkin
Given a verified account with a known password
When the client submits a login request with correct credentials
Then an access token and a refresh token are returned
And the failed-attempt counter is reset
```

### 6.1a Failed-attempt-counter reset and refresh-token persistence commit as one unit

```gherkin
Given the refresh-token persistence write would fail after the failed-attempt-counter reset commits during a successful login
When the client submits a login request with correct credentials
Then either both writes commit and a valid token pair is returned, or the whole login is rejected as a failure
And the account is never left with a reset counter but no issued, persisted refresh token
```

### 6.2 Refresh returns a new access token for a valid refresh token

```gherkin
Given a valid, unexpired refresh token from a prior login
When the client submits a refresh request with that token
Then a new access token is returned
```

### 6.3 Refresh rejects an expired or invalid refresh token

```gherkin
Given a refresh token that is expired or does not correspond to any issued token
When the client submits a refresh request with that token
Then the response is rejected, invalid refresh token
```

### 6.4 Refresh rejects a token whose claim shape no longer matches current code

```gherkin
Given a refresh token issued with a claim set that differs from what current code expects (a claim renamed, dropped, or added since issuance)
When the client submits a refresh request with that token
Then the response is a clean 401, invalid refresh token
And the server does not crash with an unhandled deserialization error
```

### 6.5 Access token is valid up to, not past, its exact expiry instant

```gherkin
Given an access token one tick before its exact expiry instant
When that token is presented to a protected endpoint
Then the request is authorized

Given the same access token one tick after its exact expiry instant
When that token is presented to a protected endpoint
Then the request is rejected as unauthorized
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|---------------------------|
| `a registration request` | POST /api/v1/auth/register |
| `the account becomes verified` / `verify request` | POST /api/v1/auth/verify |
| `requests a resend` | POST /api/v1/auth/resend-code |
| `submits a login request` | POST /api/v1/auth/login |
| `submits a refresh request` | POST /api/v1/auth/refresh |
| `the response is a validation error` | HTTP 400 |
| `rejected as a duplicate` | HTTP 409 |
| `rejected, already verified` | HTTP 409 |
| `rejected, cooldown active` | HTTP 429 |
| `rejected, account not verified` / `locked out` | HTTP 403, distinct error_code per case |
| `rejected with a generic invalid-credentials error` | HTTP 401, same error_code/message for unknown-email and wrong-password |
| `rejected, invalid refresh token` | HTTP 401 |
| `an account is created` | Row in `users` table, `is_verified=false` |
| `the failed-attempt counter` | DB column updated via atomic increment (e.g. `UPDATE ... SET count = count + 1`), never ORM load-then-save |
| `resend/verify cooldown and single-active-code invalidation` | DB-persisted, atomic conditional update — never in-process state (backend runs multiple instances) |
