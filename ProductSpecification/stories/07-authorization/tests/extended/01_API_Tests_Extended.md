> These are additional edge case tests. Implement after core tests pass.

# Authorization — API Tests (Extended)

## 1. Registration email with leading/trailing whitespace is trimmed before validation

```gherkin
Given a registration request with email "  user@example.ru  "
When the client submits the request
Then the email is trimmed before uniqueness check and storage
```

## 2. Password containing only special characters beyond the required set

```gherkin
Given a registration password meeting policy but containing unusual Unicode punctuation
When the client submits the request
Then the request is accepted, hashing handles arbitrary printable characters
```

## 3. Verification code entered with surrounding whitespace

```gherkin
Given a valid verification code with leading/trailing whitespace pasted into the field
When the client submits the verify request
Then the whitespace is trimmed and the code is accepted
```

## 4. Resend-code cooldown timer precision at the 60-second boundary

```gherkin
Given a resend was issued exactly 60 seconds ago
When the client requests another resend
Then the request is accepted, the boundary instant itself is not still in cooldown
```

## 5. Refresh token cannot be reused as an access token

```gherkin
Given a valid refresh token
When it is presented directly to a protected endpoint instead of an access token
Then the request is rejected as unauthorized
```

## 6. Multiple registrations from the same IP for different emails

```gherkin
Given several registration requests for distinct, unused emails from the same client
When each request is submitted
Then each succeeds independently, no cross-account interference
```
