# OAuth sign-in — API Tests

> **Implementation Order**: sequential TDD — `start` redirect + provider validation, then
> `exchange` branches (replay, expiry, size, empty), concurrency + atomicity, then account
> auto-creation and identity resolution.

---

## 1. Start endpoint

### 1.1 Start redirects to the provider

```gherkin
Given the OAuth providers are configured
When a visitor requests the VK start endpoint
Then the response redirects to the VK authorization page
And the client_id, redirect_uri, scope, and a CSRF state are set server-side
```

### 1.2 Unknown provider is rejected

```gherkin
When a visitor requests the start endpoint for an unknown provider
Then the request is rejected as not found
And no redirect to any provider is issued
```

---

## 2. Exchange — validation & safety

### 2.1 A valid handoff code returns a session

```gherkin
Given a freshly minted, unspent handoff code
When the code is exchanged
Then a session identical in shape to email+password login is returned
```

### 2.2 A replayed code is rejected

```gherkin
Given a handoff code that has already been exchanged once
When the same code is exchanged again
Then the request is rejected as invalid-or-expired
And no second session is issued
```

### 2.3 An expired code is rejected at the TTL boundary

```gherkin
Given a handoff code whose short TTL has just elapsed under a controlled clock
When the code is exchanged
Then the request is rejected as invalid-or-expired
And a code exchanged one instant before expiry still succeeds
```

### 2.4 An over-length code is rejected before lookup

```gherkin
When an over-length handoff code is submitted to the exchange
Then the request is rejected on the size bound
```

### 2.5 Concurrent exchanges of one code yield exactly one session

```gherkin
Given a single freshly minted handoff code
And two exchange requests for that code are held at the redeem point on different instances
When both are released to redeem simultaneously
Then the redemption is a single atomic compare-and-delete
And exactly one returns a session and the other is rejected as invalid-or-expired
And never are two sessions issued
```

### 2.7 An empty or missing code is rejected server-side

```gherkin
When an exchange request carries an empty or absent code
Then the request is rejected on the boundary
And no session is issued
```

### 2.6 A code minted on one instance is redeemable on another

```gherkin
Given a handoff code minted on one backend instance
When it is exchanged against another instance immediately after minting
Then the exchange succeeds
```

---

## 3. Account resolution

### 3.1 First sign-in auto-creates one verified account

```gherkin
Given a provider identity with no existing account
When the handoff code for that identity is exchanged
Then exactly one account is created from the provider-asserted email
And it requires no email-verification step
```

### 3.2 Concurrent first sign-ins for one identity create one account

```gherkin
Given a provider identity with no existing account
When two first-time exchanges for that identity are released simultaneously against a unique (provider, subject) constraint
Then exactly one account is created for that provider identity
And the second resolves to the same account, not a duplicate
```

The unique constraint (not timing) forces single-account — a plain check-then-insert goes red.

### 3.3 Email case / normalization / locale variance resolves to one account

```gherkin
Given a provider identity whose email differs across two sign-ins only by
  letter case (including a Turkish dotted/dotless I), or by Unicode normalization form
When each handoff code is exchanged under invariant-locale case-folding
Then both resolve to the same single account
And a stored multibyte email round-trips byte-exact after normalization
```

Turkish I/İ forces invariant-locale folding; round-trip forces NFC without mangling non-ASCII.

### 3.7 A large provider subject id is not truncated

```gherkin
Given two distinct provider subject ids both above the safe-integer boundary
When each identity's handoff code is exchanged
Then the two resolve to two distinct accounts
And a subject id above the safe-integer boundary round-trips exactly (carried as a string, not a JSON number)
```

### 3.8 OAuth email colliding with an existing password account does not overwrite it

```gherkin
Given an existing email+password account
When a handoff code whose provider email equals that account's email is exchanged
Then a new, distinct OAuth account is created (linking is deferred)
And the pre-existing email+password account is left intact — credentials unchanged, not converted or linked
```

Deferred-linking makes "leave the neighbour intact" load-bearing — also the takeover guard.

### 3.9 A failed session issue leaves no orphan account

```gherkin
Given a first-time exchange that auto-creates the account
When a later write in the same exchange unit fails
Then the whole unit rolls back and no account row remains
```

### 3.10 Recovery after a lost exchange response

```gherkin
Given an exchange that committed a session but whose response was lost
When the user restarts sign-in and completes a fresh handoff code
Then sign-in succeeds
And no duplicate account or orphaned session results
```

### 3.4 A code that yields no session is not burned

```gherkin
Given a handoff code whose redemption fails to issue a session
When the exchange is retried with the same code
Then the code has not been silently consumed and the failure is recoverable
```

### 3.5 Extra request fields cannot over-bind on auto-create

```gherkin
Given an exchange request body carrying account fields beyond the handoff code
When the code is exchanged and an account is auto-created
Then only provider-asserted attributes are bound and the extra fields are ignored
```

### 3.6 Sign-in failure copy does not reveal account existence

```gherkin
When an exchange fails for a provider identity that has an account
And when it fails for one that does not
Then the returned error copy is identical for both
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the VK start endpoint` | `GET /api/v1/auth/oauth/vk/start` |
| `the exchange` | `POST /api/v1/auth/oauth/exchange` `{ code }` |
| `a handoff code` | opaque single-use short-TTL code minted by the provider callback |
| `a session ... shape as email+password login` | `{ access_token, refresh_token, access_token_expires_at, refresh_token_expires_at }` |
| `a controlled clock` | injectable clock pinning the TTL boundary |
| `different instances` | multiple backend replicas over the shared handoff-code store |
