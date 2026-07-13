# Authorization — Security Tests

Scenarios scoped to this story's actual attack surface: password storage, JWT issuance,
brute-force/rate-limit abuse, input injection via the email field, mass assignment on
registration, and the resend/verify credential-disclosure trade-off. Generic 401
(unauthenticated), CORS, and security-header checks are cross-cutting and out of scope
here.

---

## 1. Password Hashing

```gherkin
Given a user registers with a password
When the account row is inspected
Then the stored value is a bcrypt hash, never the plaintext password
And the plaintext password never appears in any API response or log line
```

## 2. Verification Code Never Logged Beyond the Mocked Response

```gherkin
Given a user registers or requests a resend
When the resulting log output is inspected
Then the verification code appears only in the intended API response, never in a
    persisted structured log line
```

## 3. Mass Assignment on Registration

```gherkin
Given a registration request body includes is_verified, id, and created_at
When the request is processed
Then none of those attacker-supplied values are bound onto the created account
```

## 4. SQL Injection via Email Field

```gherkin
Given a registration, verify, resend, or login request whose email field contains
    SQL-metacharacter payloads
When the request is processed
Then the payload is treated as literal data, no injection occurs
And the query behaves as if the value were an ordinary (invalid) email
```

## 5. Log Injection via Email Field

```gherkin
Given a registration request whose email field contains embedded CR/LF sequences
When the request is processed and logged
Then the log output is not corrupted or forged by the embedded control characters
```

## 6. Rate Limiting — Login Brute Force

```gherkin
Given repeated failed login attempts against one account
When the configured consecutive-failure threshold is reached
Then further login attempts are rejected regardless of correct credentials, until the
    cooldown elapses
```

## 7. Rate Limiting — Resend-Code Abuse

```gherkin
Given a resend-code request has just succeeded for an account
When another resend-code request is submitted within 60 seconds
Then the request is rejected, cooldown active
```

## 8. JWT — Algorithm and Expiry Enforcement

```gherkin
Given a JWT access token signed with an unexpected algorithm (e.g. "none")
When the token is presented to a protected endpoint
Then the token is rejected, the algorithm is not trusted from the token header

Given a JWT access token past its expiry time
When the token is presented to a protected endpoint
Then the request is rejected as unauthorized
```

## 9. Refresh Token Rejected After Signing-Key Rotation

```gherkin
Given a refresh token was issued under a signing key that has since been rotated
When the token is presented to /auth/refresh
Then the response is a clean 401, not a server error
```

## 10. Resend/Verify Credential Disclosure — Documented, Rate-Limited Exposure

```gherkin
Given an attacker knows a victim's registered email but not their password
When the attacker calls resend-code for that email
Then the response includes a live verification code for the victim's account
    (accepted trade-off of the mocked-email design — see 07_Authorization_Notes.md)
And the 60-second cooldown is the only throttle on repeated attempts against that email
```

## 11. Sentinel Secret Absent From Every Failure Path

```gherkin
Given a known sentinel password and a known sentinel verification code are seeded for a
    test account
When each failure path is triggered in turn — wrong password, wrong code, expired code,
    locked-out login, unverified-account login, invalid refresh token
Then the sentinel value never appears in that response body
And the sentinel value never appears in the resulting log output
```

## 12. Fail-Closed Paths Emit a Distinguishable Signal

```gherkin
Given the lockout-state read fails during a login attempt
And, separately, the is_verified-state read fails during a login attempt
When each failure is triggered
Then each emits a distinct, attributable error signal (metric or log entry) that a
    normal locked-out or not-verified response does not also emit
And the two failure paths are distinguishable from each other in that signal
```
