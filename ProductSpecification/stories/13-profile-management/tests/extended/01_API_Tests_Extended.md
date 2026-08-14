> These are additional edge case tests. Implement after core tests pass.

# Profile management — API Tests (Extended)

---

## 1. Method and Content Surface

### 1.1 Methods this contract does not define are refused as such
```gherkin
Given an authenticated account
When it posts to the profile path
And when it puts to the profile path
And when it deletes the profile path
Then each is refused as a method the route does not offer
```

### 1.2 Unknown keys alongside a valid name are ignored, not refused
```gherkin
Given an authenticated account
When it submits a valid name alongside a key this contract does not define
Then the rename is accepted
And a fresh read of the stored profile shows only the name changed
```

### 1.3 A body that is legal in size but pathological in shape is bounded in cost
```gherkin
Given an authenticated account
When it submits a valid name in a body under the request body cap that is deeply nested
And in a body under the cap carrying tens of thousands of unknown keys
Then each request either is refused or completes within its stated wall-clock bound
And concurrent callers are unaffected while it is handled
```

*1.2 makes unknown keys legal and ignored, which is the right contract and also the opening:
a body well under the size cap can still be arbitrarily expensive to parse, on the product's
highest-rate endpoint. The size cap bounds bytes, not shape.*

---

## 2. Name Content Edges

### 2.1 A grapheme cluster spanning several code points is bounded as written
```gherkin
Given an authenticated account
When it submits a name of joined emoji whose code point count is exactly the bound
Then the rename is accepted
And a fresh read of the stored profile returns it unchanged
```

### 2.2 Interior whitespace is preserved while surrounding whitespace is trimmed
```gherkin
Given an authenticated account
When it submits a name with several spaces between two words and spaces at both ends
Then the rename is accepted
And a fresh read of the stored profile shows the interior spacing preserved
And shows no leading or trailing whitespace
```

### 2.3 A name of a single character is accepted
```gherkin
Given an authenticated account
When it submits a name of one visible character
Then the rename is accepted
And a fresh read of the stored profile returns that character
```

### 2.4 Renaming to the value already stored is accepted and changes nothing
```gherkin
Given an authenticated account that has set a name
When it submits that same name again
Then the rename is accepted
And a fresh read of the stored profile shows that name
```

### 2.5 Clearing a name that was never set is accepted
```gherkin
Given an authenticated account that has never set a name
When it submits an empty name
Then the request is accepted
And a fresh read of the stored profile still reports no name
```

---

## 3. Last-Write-Wins, Observed

### 3.1 The later rename wins and the earlier one is silently lost
```gherkin
Given an authenticated account renamed from one client and then from another
When both renames have completed
Then a fresh read of the stored profile reports the later name
And no conflict is reported to either client
```

*Recorded so last-write-wins reads as the decision it is (`endpoints.md`), not as a missed
hazard. Note this is not a concurrency guard — issuing two renames together serializes.*

### 3.2 A stale client can clear a name another client just set
```gherkin
Given an authenticated account renamed by one client
When a second client that still believes the name is unset submits a clearing
Then the clearing is accepted
And a fresh read of the stored profile reports no name
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the profile path` | `/api/v1/auth/me` |
| `joined emoji` | ZWJ sequence — several code points, one rendered grapheme |
| `the bound` | 60 code points after trim + NFC |
| `a fresh read of the stored profile` | Re-read through a new session against real Postgres |
