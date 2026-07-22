# OAuth sign-in — Infrastructure Tests

---

## 1. Handoff-code store failure

### 1.1 An exchange fails closed when the code store is unavailable

```gherkin
Given the shared handoff-code store is unavailable
When a handoff code is exchanged
Then the exchange fails closed with a server error
And no session is issued on the unverified path
```

---

## 1a. Failure observability

### 1a.1 Fail-closed branches emit an attributable operator signal

```gherkin
Given the code store is unavailable, or the provider times out, on an exchange
When the request fails closed
Then an error metric or correlation-id-keyed log signal is emitted for that failure class
And a successful sign-in emits no such failure signal
```

Because the code/token must never be logged, the operator signal is a metric / correlation
id — a spike in fail-closed responses must not be invisible.

---

## 2. OAuth configuration validation

### 2.1 Missing OAuth provider config fails fast at startup

```gherkin
Given a required OAuth provider setting (redirect_uri, scope, or client secret) is unset or blank
When the application starts
Then startup fails loud with a clear configuration error
And the app never falls back to a development redirect target at first sign-in
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the shared handoff-code store` | DB/cache backing the single-use code (never in-process) |
| `a required OAuth provider setting` | `infra/.env` OAuth keys for VK/Yandex |
