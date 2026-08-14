<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/05_Security_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Profile management — Security Tests

Scoped to this story's actual attack surface. Not included: generic unauthenticated 401s,
security headers, CORS and HTTPS (cross-cutting, tested globally); SQL injection (the ORM
parameterizes, and the scan dismissed it with that reason); account enumeration (no route
takes an account identifier, so there is nothing to enumerate — 1.3 is the guard that it
stays that way); session fixation (bearer tokens, no server session).

The dominant risk here is **stored XSS with the widest blast radius in the application**:
the name is free-form user text echoed into a header that renders on every page, with length
as the only input restriction by design. The whole escaping burden therefore sits at output,
across two sinks.

---

## 1. Authorization Surface

### 1.1 A caller can never read another account's profile
```gherkin
Given two accounts each holding a valid access token
When each reads its profile
Then each receives only its own email, name and registration date
And neither response contains the other's address or name
```

### 1.2 A caller can never write another account's profile
```gherkin
Given two accounts each holding a valid access token
When one renames itself while naming the other's identifier in the body
And when it renames itself while naming the other's identifier in the query
Then only its own name changes
And a fresh read of the other account's stored profile is unchanged
```

### 1.3 Neither route accepts an account identifier as a parameter
```gherkin
Given the profile routes as published
Then neither takes an account identifier in its path
And neither takes an account identifier in its query
And the account is resolved solely from the presented token
```

### 1.4 A token that is not a live access token is refused identically in every case
```gherkin
Given a refresh token, a token with no type claim, a token with an unknown type claim
And a structurally valid token whose account row is gone, and a forged token
When each is presented to read and to rename
Then every attempt is refused as unauthorized
And the refusals are indistinguishable from one another
```

### 1.5 The account check denies when its own database access fails
```gherkin
Given the account-existence check's database access made to fail
And separately, made to time out waiting for a connection
When an authenticated account reads its profile and renames itself
Then every attempt is refused as unauthorized
And the refusal is indistinguishable from a forged token's
And no name is written
```

*This check runs on its own session, separate from the profile read (`endpoints.md`), so it
is a guard with an independently failing backing store. Exhausting the pool and asserting
"the request fails" does not cover it: on the read path that failure is equally explained by
the profile read dying downstream, so the scenario stays green on an existence check that
swallows its error and answers "the account exists".*

---

## 2. Mass Assignment

### 2.1 Only the name is writable through the rename route
```gherkin
Given an authenticated account
When it submits a valid name alongside a verification status, an email, a password,
  a registration date, a failed-attempt count and an account identifier
Then a fresh read of the stored row shows only the name changed
And its verification status is unchanged
```

*The response is described as "the profile", which invites reusing the response model for
the request; that model plus a repository update branch that rewrites the aggregate is a
direct path to `is_verified` or `email` being set from a request body
(`13_ProfileManagement_Notes.md` § Security Considerations).*

---

## 3. Stored Cross-Site Scripting

### 3.1 A name carrying markup renders as text in every sink
```gherkin
Given an account whose stored name is a script tag
And an account whose stored name is an attribute-breaking fragment
When each signs in and their pages render
Then the name appears literally as text in the header
And it appears literally as text on the profile screen
And it appears literally inside the avatar's accessible label
And no element is created and no handler is bound from that value
```

*Three sinks, not one: element text, the profile field, and the `aria-label`/`title`
attribute on the avatar. An attribute sink escapes differently from a text sink, so one
assertion does not cover the other. No raw-HTML rendering may be used on this value.*

### 3.1a The address is the second hostile value into the same three sinks
```gherkin
Given an account whose registered address contains markup
And an account whose registered address contains an attribute-breaking fragment
When each signs in with no name set and their pages render
Then the address appears literally as text in the header identity row
And it appears literally as text on the profile screen
And it appears literally inside the avatar's accessible label
And no element is created and no handler is bound from that value
```

*With no name set — the state of every new account — the address **is** the rendered identity
and the initials source. Every markup scenario feeds the name; whether the address value
object forbids these characters is the unstated assumption this pins.*

### 3.2 A bidirectional override in a name cannot reorder the surrounding header
```gherkin
Given an account whose stored name contains a right-to-left override character
When its page renders
Then the header text around the name reads in its original order
```

*Not the same guard as 3.1 and not satisfied by escaping — the character is legal text. It
needs bidi isolation at the sink.*

### 3.3 A name that renders as nothing cannot be stored
```gherkin
Given an authenticated account
When it submits a name made only of invisible characters
Then the name is cleared rather than stored
And the identity row falls back to the address
And the avatar's accessible label still names an account
```

*An invisible name is worse than no name: it blanks the identity row and truncates the
accessible label to a bare prefix, destroying the one job that row has.*

---

## 4. Input Bounds

### 4.1 The name is bounded at every layer that can be reached
```gherkin
Given an authenticated account
When it submits a raw name past the input cap
And it submits a normalized name past the name bound
And it submits a body far past the request body cap
Then each is refused
And the raw cap refusal is reached before normalization runs
And nothing is persisted in any case
```

### 4.2 A refusal never echoes the rejected input back
```gherkin
Given an authenticated account
When it submits a name past the bound
And it submits a value that is not a string as the name
Then each refusal carries only a failure code and a message
And neither refusal repeats the submitted value
```

*The framework's own validation failure does echo the input, which is why these must reach
the domain path rather than that one (`endpoints.md`).*

---

## 5. Disclosure of Personal Data

### 5.1 Neither route's response may be cached
```gherkin
Given an authenticated account
When it reads its profile and when it renames itself
Then every response of both routes forbids storing the body
And that holds for refusals as well as successes
```

### 5.2 No failure path logs or returns the account's identity
```gherkin
Given an account seeded with a distinctive email and a distinctive name
When it is refused as unauthorized, refused for an over-long name, and made to fail as a server fault
Then neither value appears in any response body
And neither value appears in the captured application log
```

### 5.2a Redaction replaces the value rather than merely omitting it
```gherkin
Given an account seeded with a distinctive email, a distinctive name and a distinctive token
When each failure family is provoked in turn
Then the log shows the agreed redaction marker where each value would have stood
And no response body or log record carries any escaped, percent-encoded or base64 form of them
```

*5.2 asserts absence of the raw string, which any encoding change satisfies. The bearer token
is included because the ordinary way it leaks is a warning line echoing the rejected
authorization header.*

### 5.3 Signing out leaves no identity behind on a shared machine
```gherkin
Given a signed-in user whose profile has been read
When they sign out and no one signs in afterwards
Then no browser storage key holds their address or name
And no rendered element holds either value
```

*The account-switch case does not cover this one: there, the next sign-in overwrites the
snapshot. Here nothing overwrites it.*

### 5.4 An account switch in one tab never shows the previous account's identity
```gherkin
Given a signed-in user whose profile read is still in flight
When they sign out and sign in as a different account in the same tab
And the first account's profile response then arrives
Then the header shows the second account's identity
And a header mounting after the switch shows the second account's identity
And the first account's address and name appear nowhere on the page
```

*A cross-account identity leak, strictly worse than a stale name.*

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a valid access token` | Access-typed JWT from the sign-in flow |
| `reads its profile` / `renames itself` | `GET` / `PATCH /api/v1/auth/me` |
| `a fresh read of the stored row` | Direct row select through a new session against real Postgres |
| `an attribute-breaking fragment` | `" onmouseover="alert(1)` |
| `a right-to-left override character` | U+202E — needs `<bdi>` or `unicode-bidi: isolate`, not escaping |
| `invisible characters` | U+200B, U+FEFF, U+00A0, U+3164, U+2800 |
| `the avatar's accessible label` | `aria-label` / `title` on `ProfileAvatar` («Меню профиля: …») |
| `the input cap` / `the name bound` | 256 raw code points / 60 normalized code points |
| `the request body cap` | 2 MiB application cap; proxy cap set above it |
| `forbid storing the body` | `Cache-Control: no-store` |
| `the captured application log` | Log appender captured for the duration of the request |
| `browser storage key` | `sessionStorage` and `localStorage` after `clearSession()` |
