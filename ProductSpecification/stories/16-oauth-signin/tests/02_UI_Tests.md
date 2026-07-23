# OAuth sign-in — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the login-screen button display, then the click→navigation, then the
> `/auth/callback` exchange flow (loading → success), then the error/replay/network
> branches, then redirect safety and the no-regression guard.

---

## 1. Page Display

### 1.1 Login screen shows both OAuth provider buttons

```gherkin
Given a visitor opens the login screen
Then a "Войти через VK ID" button is shown below the email/password form
And a "Войти через Yandex ID" button is shown below it
And both are visually distinct from the primary "Войти" submit button
```

---

## 2. Navigation to the provider

### 2.1 VK button starts the VK handshake

```gherkin
Given a visitor on the login screen
When the visitor clicks "Войти через VK ID"
Then the browser navigates the full page to the VK start endpoint
And no background request is issued from the page
```

### 2.2 Yandex button starts the Yandex handshake

```gherkin
Given a visitor on the login screen
When the visitor clicks "Войти через Yandex ID"
Then the browser navigates the full page to the Yandex start endpoint
```

---

## 3. Callback success flow

### 3.1 Valid handoff code signs the user in

```gherkin
Given the visitor lands on the OAuth callback screen with a valid handoff code
Then a loading state is shown while the exchange is in progress
When the exchange returns a valid session
Then the session is stored
And the user is taken to the authenticated app shell
And the browser history is replaced so Back does not return to the callback
```

### 3.2 The exchange is issued exactly once per callback mount

```gherkin
Given the visitor lands on the OAuth callback screen with a valid handoff code
When the callback screen mounts and its effect runs twice
Then exactly one exchange request is issued for that code
```

### 3.3 A late duplicate rejection after a stored success is ignored

```gherkin
Given the callback exchanged a handoff code and stored a session
When a duplicate exchange for the same code later rejects as already-used
Then the user remains in the authenticated app shell
And is not bounced back to the login screen
```

---

## 4. Callback error handling

### 4.1 Provider error / user-cancel returns to login with a distinct message

```gherkin
Given the visitor lands on the OAuth callback screen with an error parameter
Then the user is returned to the login screen
And a distinct "не удалось войти через провайдера" message is shown
And it is not a wrong-password / validation-style message
```

### 4.2 Exchange network or server failure is retry-affording

```gherkin
Given the visitor lands on the OAuth callback screen with a valid handoff code
When the exchange fails with a network, timeout, or server error
Then the user is returned to the login screen with a retry-capable error
And an indefinite spinner is never shown
```

### 4.3 A replayed or expired code shows an error, not a second sign-in

```gherkin
Given the visitor re-opens the OAuth callback screen with an already-used handoff code
When the exchange rejects the code as used or expired
Then an error is shown and no new session is created
```

### 4.4 A malformed callback resolves to the error state without an exchange

```gherkin
Given the visitor lands on the OAuth callback screen
When the provider is unknown, or the code is missing, empty, or over the length bound
Then the error state is shown
And no exchange request is issued
```

### 4.5 An unrecognized error code falls back to generic copy

```gherkin
Given the visitor lands on the OAuth callback screen with an unrecognized error code
Then a generic sign-in-failed message is shown
And the raw error value is never rendered on screen
```

### 4.6 A 200 exchange without a usable token fails closed

```gherkin
Given the visitor lands on the OAuth callback screen with a valid handoff code
When the exchange returns 200 with a body whose access token is absent, null, or empty
Then no session is stored
And the user is returned to the login error state, never the app shell
```

---

## 5. Redirect safety

### 5.1 The post-sign-in redirect target is validated

```gherkin
Given the visitor lands on the OAuth callback screen with a valid handoff code
And a crafted external redirect target is present in the callback state
When the sign-in succeeds
Then the user is taken to the in-app app shell default
And is never redirected to the external target
```

---

## 6. No regression

### 6.1 Email + password login is unchanged

```gherkin
Given a verified email+password user on the login screen
When the user signs in with correct credentials
Then the user is taken to the authenticated app shell as before
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the login screen` | `/login` route rendering `LoginForm` |
| `the OAuth callback screen` | `/auth/callback` route component |
| `a valid handoff code` | `?code=<opaque>` param, exchange mock resolves a session |
| `the VK/Yandex start endpoint` | `GET /api/v1/auth/oauth/{vk\|yandex}/start` (full-page nav) |
| `the exchange` | `POST /api/v1/auth/oauth/exchange` `{ code }` |
| `the session is stored` | `authSession` (sessionStorage) holds access+refresh JWT |
| `an error parameter` | `?error=<code>` on the callback URL |
| `the app shell default` | `safeRedirectTarget` fallback in-app path |
