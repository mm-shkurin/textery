# Authorization — Integration Tests

This story has no live external API (verification email is mocked, no OAuth provider is
in scope — see `interview.md`), so the usual "external API success/error/timeout"
scenarios don't apply. The one integration seam this story owns end-to-end is the
token-issuance-then-refresh pipeline.

## 1. Full Register → Verify → Login → Refresh Pipeline

```gherkin
Given a new email and a policy-compliant password
When the client registers, reads the mocked code from the response, verifies it, logs
    in, and then refreshes the resulting access token
Then every step succeeds in sequence
And the final refreshed access token is valid against a protected endpoint
```

## 2. Refresh Token Reuse After Access Token Expiry

```gherkin
Given a valid refresh token obtained from a login
And the access token from that same login has since expired
When the client calls /auth/refresh with the refresh token
Then a new, valid access token is issued
And the previously expired access token is not required for this exchange
```

## 3. Login Immediately Usable Against a Protected Route

```gherkin
Given a login has just returned an access token
When that token is presented to a protected route
Then the request is authorized, no propagation delay between issuance and validity
```
