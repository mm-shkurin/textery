# OAuth sign-in — Security Tests

Story-specific attack surface only. Generic 401/headers/CORS/HTTPS are tested globally.

---

## 1. Open redirect

### 1.1 A crafted callback redirect target cannot drive an external redirect

```gherkin
Given the OAuth callback carries a crafted external redirect target
When the sign-in completes
Then the user is sent only to an in-app path
And never to the external target
```

---

## 2. Output encoding

### 2.1 The callback error value is never rendered raw

```gherkin
Given the OAuth callback carries an error value containing markup
Then the error state renders generic copy
And the markup is never injected into the page
```

---

## 3. Handoff-code handling

### 3.1 The handoff code is single-use

```gherkin
Given a handoff code that has been exchanged once
When it is presented again
Then it is rejected and yields no session
```

### 3.2 The handoff code and tokens never appear in a URL or log

```gherkin
Given a completed OAuth sign-in
Then no access or refresh token appears in any URL, browser history, or log line
And the handoff code is never written to a persisted log
And the spent code is removed from history after exchange
```

---

## 4. CSRF state

### 4.1 A callback with an invalid or missing state is rejected

```gherkin
Given a provider callback whose CSRF state is missing or does not match
Then the handshake is rejected
And no account is created and no session is issued
```

---

## 5. Abuse / rate limiting

### 5.1 Repeated OAuth requests are rate-limited

```gherkin
Given repeated requests to the start / callback / exchange endpoints from one source
When the requests exceed the configured rate
Then further requests are throttled
```

---

## 6. Mass assignment

### 6.1 Privileged fields in the exchange body are ignored

```gherkin
Given an exchange request body carrying a privileged or server-owned account field
When the code is exchanged and an account is auto-created
Then the persisted account ignores the injected field
```

---

## 7. Error-path disclosure

### 7.1 Failure responses carry no internal detail

```gherkin
Given a sentinel is seeded into the store, provider response, and code values
When any OAuth failure path returns (store unavailable, provider error/timeout, exchange 5xx)
Then the response body matches the generic client-safe error schema
And carries no stack trace, SQL fragment, internal class name, file path, or raw upstream provider text
And the provider email (PII) and the handoff code never appear in the response or captured log output
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the OAuth callback` | `GET /api/v1/auth/oauth/{provider}/callback` and the frontend `/auth/callback` |
| `a handoff code` | opaque single-use short-TTL code |
| `the exchange` | `POST /api/v1/auth/oauth/exchange` |
| `the start / callback / exchange endpoints` | the three `/api/v1/auth/oauth/*` routes |
