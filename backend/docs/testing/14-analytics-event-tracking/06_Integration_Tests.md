<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/06_Integration_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Analytics Event Tracking — Integration Tests

Two integrations: the geolocation dependency this story introduces on the registration path,
and the existing OAuth handshake, which this story extends so a provider-created account is
not born without attribution.

---

## 1. Geolocation

### 1.1 A located address is stored as its country
```gherkin
Given the geolocation dependency resolves a public address to a country
When a visitor registers from that address
Then the account stores that country
```

### 1.2 Every failure mode leaves registration whole and the country unset
```gherkin
Given the geolocation dependency refuses the request
And the geolocation dependency answers with a server error
And the geolocation dependency answers with something unreadable
When a visitor registers under each condition
Then every registration succeeds normally
And every account's country is unset
And each failure is reported
```

### 1.3 A failing dependency is asked once, not repeatedly
```gherkin
Given the geolocation dependency answers with a server error
And separately, refuses the request
When a visitor registers under each
Then the dependency received exactly one request per registration
And the registration answers within its normal budget
And the account's country is unset
```

1.2 asserts the *outcome* of each failure mode is identical; it never counts the calls. An
adapter whose default policy retries a server error three times passes it, and multiplies the
configured timeout — which is what breaks the registration budget.

### 1.4 A dependency that does not answer is abandoned, not waited on
```gherkin
Given the geolocation dependency does not answer
When a visitor registers
Then the registration answers within its normal budget
And the account's country is unset
And nothing is committed after the caller has stopped waiting
```

### 1.5 The address the dependency is asked about is the caller's, not a proxy's
```gherkin
Given a request arriving through the deployment's proxy chain
When a visitor registers
Then the address the dependency is asked about is the one the proxy contract designates
And that same address is what the account stores
```

The extraction is the one already used for sign-in abuse bounds, whose own documentation
calls it a best-effort measure that no security invariant rests on. This story makes its
output durable business data, so which hop is trusted stops being a detail.

---

## 2. OAuth Sign-In

### 2.1 Attribution carried into the handshake reaches the created account
```gherkin
Given a visitor holding frozen campaign parameters
When it begins a provider sign-in carrying them
And the provider returns it to the callback
And the account is created
Then the account carries those campaign parameters
```

### 2.2 Attribution parked on one instance is read back by another
```gherkin
Given a visitor beginning a provider sign-in carrying campaign parameters on one instance
When the provider returns it to a callback served by a second instance that never handled the start
Then the account is created
And it carries those campaign parameters
```

`endpoints.md` calls parking the parameters on the handshake row «the most consequential call
in this step». Every other scenario runs the start and the callback in one process, so an
in-memory map keyed by handshake token passes all of them — including the no-leak-between-
visitors case — while losing attribution on every real multi-instance sign-up.

### 2.3 The campaign parameters are never handed to the provider
```gherkin
Given a visitor beginning a provider sign-in carrying campaign parameters
When the handshake begins
Then the address the visitor is sent to carries no campaign parameters
```

### 2.4 A first provider sign-in records both events; a later one records only the sign-in
```gherkin
Given a visitor arriving through a provider for the first time
When the callback completes
Then a completed registration and a successful sign-in are both recorded
And both carry the identical moment
When the same account later signs in through that provider
Then only a successful sign-in is recorded
```

### 2.5 A callback arriving just inside the handshake's lifetime keeps the attribution
```gherkin
Given a provider sign-in begun with campaign parameters
And the clock advanced to just before the handshake expires
When the callback completes
Then the account is created carrying all five values
When the clock is advanced one tick past expiry instead
Then the callback is refused and no account is created
```

The handshake's expiry now gates business data, not just a security token. Only the
past-expiry side was pinned; an expiry mis-sized, or evaluated against a different clock than
the one that wrote the row, silently strips attribution from the whole provider channel.

### 2.6 A provider-created account carries the same technical context as a registered one
```gherkin
Given a visitor arriving through a provider, from a locatable address, with a device and a language
When its account is created
Then the account stores the address, country, device, operating system and language
```

The callback is itself a browser request, so the technical context is available there exactly
as it is at registration. Only the campaign parameters need carrying through the handshake —
without this scenario the whole provider channel registers with an empty context and nothing
in the data reveals it.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the geolocation dependency resolves…` | `GeoLocationPort` fake returning a known country |
| `refuses the request` / `server error` / `unreadable` | Port fake raising the adapter's 4xx, 5xx and malformed-response failures |
| `received exactly one request per registration` | Call count on the port fake, asserted per registration |
| `does not answer` | Port fake hanging past the configured timeout |
| `nothing is committed after the caller has stopped waiting` | No `accounts` row after the client-side deadline aborts the request |
| `the deployment's proxy chain` | Multi-hop `X-Forwarded-For`; the trusted hop per the contract named in `endpoints.md` |
| `begins a provider sign-in carrying them` | `GET /api/v1/auth/oauth/{provider}/start` with the five `utm_*` query parameters |
| `a second instance that never handled the start` | A separate session/process sharing only the database — the start's process state gone |
| `the address the visitor is sent to` | The `Location` header of the 302 to the provider |
| `both carry the identical moment` | One `Clock` reading passed to both emissions; byte-equal `event_time` |
| `the clock advanced to just before the handshake expires` | Injected `Clock` stub at the `oauth_states` expiry boundary |
