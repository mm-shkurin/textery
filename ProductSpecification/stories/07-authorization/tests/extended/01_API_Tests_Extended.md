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

## 7. Email local-part containing control or bidi-control characters is rejected

```gherkin
Given a registration request with an email local-part containing a CR/LF, NUL, or bidi-control/zero-width Unicode codepoint
When the client submits the request
Then the request is rejected as INVALID_EMAIL, not accepted-then-relied-on-for-escaping-elsewhere
```

## 8. Visually-confusable emails in different scripts are distinct accounts

```gherkin
Given an account already exists for a Latin-script email local-part
When a registration request is submitted for the visually-identical Cyrillic-script local-part (different codepoints, NFC-normalized)
Then the request succeeds as a separate account -- homograph pairs are distinct by codepoint, not merged by appearance
```

## 9. Concurrent registration with NFC vs NFD forms of the same new email

```gherkin
Given two registration requests fire at the same instant for a brand-new email, one in NFC form and one in NFD form
When both are submitted via asyncio.gather
Then exactly one succeeds (201) and the other is rejected as a duplicate (409 EMAIL_ALREADY_REGISTERED)
```
