<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — Integration Tests (Extended)

> **UNBLOCKED 2026-08-19.** The contradiction is resolved in the only direction that keeps an
> existing route's behaviour: the handshake **proceeds with the attribution dropped**. See
> `endpoints.md` § "Attribution is fail-open on both auth routes".

---

## 1. Geolocation Responses at the Edges

### 1.1 A country the taxonomy does not recognise is stored as unset, not guessed
```gherkin
Given the geolocation dependency answers with a code outside the expected set
When a visitor registers
Then the account's country reads as unset
And the unexpected answer is reported
```

### 1.2 An answer that arrives just inside the deadline is used
```gherkin
Given the geolocation dependency answers just before its deadline
When a visitor registers
Then the account stores the resolved country
And the registration answers within its normal budget
```

### 1.3 A dependency that is slow does not compound across concurrent registrations
```gherkin
Given the geolocation dependency answers slowly but within its deadline
When several visitors register at once
Then every registration answers within its budget
And none waits on another's lookup
```

---

## 2. OAuth Handshake Edges

### 2.1 Attribution parked against a handshake does not leak between visitors
```gherkin
Given two visitors beginning provider sign-ins carrying different campaign parameters
When both callbacks complete
Then each created account carries its own visitor's parameters
```

### 2.2 A handshake that is never completed leaves nothing behind
```gherkin
Given a visitor beginning a provider sign-in carrying campaign parameters
When the handshake expires without a callback
Then no account is created
And the parked parameters are not retained past the handshake's own lifetime
```

### 2.3 A provider sign-in with no campaign parameters creates an account with none
```gherkin
Given a visitor with no frozen campaign parameters
When it signs in through a provider for the first time
Then the account is created
And its campaign values read as unset
```

### 2.4 Campaign parameters over the bound do not break the handshake
```gherkin
Given a visitor beginning a provider sign-in carrying campaign parameters past the bound
When the handshake begins
Then the visitor is redirected to the provider exactly as with no campaign parameters
And the handshake route answers no status code it does not answer without them
When the callback completes and creates the account
Then the account is created
And all five campaign values read as unset
And no truncated value is stored
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a code outside the expected set` | A value the country taxonomy does not contain |
| `just before its deadline` | Fake port answering at the configured timeout minus a margin |
| `parked against a handshake` | The `utm_*` stored on the `oauth_states` row |
| `the handshake expires without a callback` | `oauth_states` row past its expiry, never consumed |
| `redirected exactly as with no campaign parameters` | Same `302` and same `Location` host/path/query as the identical request without the `utm_*` — asserted against that request |
| `answers no status code it does not answer without them` | `302 / 404 / 500` only; a `400` from this route fails the scenario |
