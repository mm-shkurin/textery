<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/extended/05_Security_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Profile management — Security Tests (Extended)

---

## 1. Output Sinks Beyond the Header

### 1.1 A name carrying markup renders as text wherever else identity is shown
```gherkin
Given an account whose stored name is a script tag
When any page that shows the account's identity renders
Then the name appears literally as text in every such place
And no element is created and no handler is bound from that value
```

### 1.2 A name carrying a line break does not forge a second log record
```gherkin
Given an account whose stored name contains line breaks and a fabricated log prefix
When an operation involving that account is logged
Then the log holds one record for that operation
And the fabricated prefix does not appear as a record of its own
```

---

## 2. Impersonation Through Look-Alikes

### 2.1 A look-alike name is stored as written, not silently folded
```gherkin
Given an authenticated account
When it submits a name using characters that look like another alphabet's
Then the rename is accepted
And a fresh read of the stored profile returns exactly what was submitted
```

*Recorded rather than guarded: display names are not identifiers on this product, so
homoglyph folding would cost more than it buys. The guard is that nothing silently rewrites
the value — a rewrite would break the round-trip assertions the main files rely on.*

---

## 3. Token Handling Edges

### 3.1 A malformed authorization header is refused like a missing one
```gherkin
Given a header carrying a token with no scheme
And a header carrying a scheme this product does not use
And a header carrying a scheme with an empty token
When each is presented to read and to rename
Then every attempt is refused as unauthorized
```

### 3.2 A token signed with the wrong key or algorithm is refused
```gherkin
Given a token signed with a different key
And a token whose signature algorithm was swapped
When each is presented to read the profile
Then both are refused as unauthorized
```

---

## 4. Storage Hygiene

### 4.1 The identity snapshot never outlives the session it belongs to
```gherkin
Given a signed-in user whose profile has been read
When the session ends for any reason
Then no browser storage key holds their address or name
```

### 4.2 A refused rename leaves the shared identity snapshot untouched
```gherkin
Given a signed-in user whose header shows their saved name
When a rename is refused as invalid
Then the header still shows the previously saved name
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `reads` / `renames` | `GET` / `PATCH /api/v1/auth/me` |
| `a fabricated log prefix` | Newline plus a forged level/timestamp prefix in the name value |
| `characters that look like another alphabet's` | Cyrillic/Latin homoglyphs (е/e, а/a) |
| `a scheme this product does not use` | e.g. `Basic`, `Token` |
| `browser storage key` | `sessionStorage` and `localStorage` |
| `the shared identity snapshot` | The single `/me`-backed identity store the header and screen read |
