# OAuth sign-in — Integration Tests

Exercise the backend↔provider handshake through a provider fake. `provider` ∈ `vk | yandex`.

---

## 1. Provider success flow

### 1.1 A valid provider authorization completes sign-in

```gherkin
Given the provider fake authorizes the user and returns a verified email
When the provider redirects to the backend callback with a valid code and state
Then the backend mints a handoff code
And redirects to the frontend callback with that code
And the subsequent exchange returns a session
```

---

## 2. Provider error handling

### 2.1 A provider error is surfaced as a callback error

```gherkin
Given the provider fake returns an error or the user cancels
When the provider redirects to the backend callback with an error
Then the backend redirects to the frontend callback with an error parameter
And no account is created and no session is issued
```

### 2.2 A provider that returns no verified email is rejected

```gherkin
Given the provider fake returns no email or an unverified email
When the backend processes the callback
Then sign-in is rejected with an error redirect
And no account is auto-created
```

---

## 3. Provider timeout

### 3.1 A slow provider token exchange fails cleanly

```gherkin
Given the provider fake does not respond within the backend's timeout
When the backend attempts the provider token exchange
Then the handshake fails closed with an error redirect
And no partial account or orphan handoff code remains
And the backend's connection-pool checkout returns to baseline (no leaked in-flight hold)
And the shared HTTP client is reused, not created per call
```

Note: the backend must NOT auto-retry the provider token exchange in a synchronized burst;
if a transient retry is added later, it requires backoff+jitter / capped attempts (own guard).

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the provider fake` | test double for the VK/Yandex OAuth endpoints |
| `the backend callback` | `GET /api/v1/auth/oauth/{provider}/callback` |
| `the frontend callback` | `/auth/callback?code=…` or `?error=…` |
| `the exchange` | `POST /api/v1/auth/oauth/exchange` |
