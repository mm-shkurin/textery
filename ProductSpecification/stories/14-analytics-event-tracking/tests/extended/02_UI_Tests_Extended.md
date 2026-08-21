> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — UI Tests (Extended)

> **UNBLOCKED 2026-08-19.** Both outcomes are now recorded in `endpoints.md` § "The five
> decisions the test spec was blocked on": an unreadable or over-bound campaign parameter is
> **not frozen and not stored**, and the visitor's journey is untouched.

---

## 1. Several Tabs at Once

### 1.1 Two tabs opening together settle on one visitor identity
```gherkin
Given a browser that has never visited the site
When two tabs open the landing page at the same moment
Then the browser holds exactly one stored visitor identity
And both tabs report their site visit under that identity
```

### 1.2 A second tab stops using an identity a first tab has erased
```gherkin
Given two open tabs sharing a visitor identity
When the account is deleted in the first tab
Then the second tab no longer reports under the erased identity
```

### 1.3 Two tabs arriving from different campaigns freeze one set
```gherkin
Given a browser that has never visited the site
When two tabs open the site from links carrying different campaign parameters
Then the browser holds exactly one campaign set
And a registration from either tab carries that set
```

---

## 2. Hostile and Awkward Entry Points

### 2.1 Campaign parameters that are not valid text are not frozen
```gherkin
Given a marketing link whose campaign parameters are encoded in a legacy character set
When the visitor arrives from it
Then the browser holds no campaign parameters
And no unreadable value is frozen as the visitor's permanent attribution
And the page loads and behaves as it does for a visitor arriving with no parameters
When the visitor later arrives from a readable campaign link
Then that set becomes the first touch
```

The last two lines are the reason for choosing "not frozen" over "frozen as replacement
characters": mojibake would occupy the first-touch slot permanently, and first-touch is never
overwritten.

### 2.2 Campaign parameters far over the bound do not become a frozen value
```gherkin
Given a marketing link whose campaign parameters are far longer than the bound
When the visitor arrives from it
And it registers
Then the registration succeeds
And the account's campaign values read as unset
And no truncated value is stored
And nothing about the arrival or the registration is visible to the visitor
```

---

## 3. Recovery Paths

### 3.1 Recovering from an editor crash does not re-report the opening
```gherkin
Given a signed-in account that has opened a document in the editor
When the editor fails and the visitor recovers through the offered action
And it opens the same document again
Then the number of reported editor openings matches the number of times the document was opened
```

### 3.2 A reload during a failed send does not duplicate the visit
```gherkin
Given a visitor whose site visit report failed
When it reloads the page
Then the number of recorded site visits matches the number of loads that succeeded in reporting
And no occurrence is recorded twice
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `at the same moment` | Two client contexts over one shared storage, both starting empty |
| `no longer reports under the erased identity` | `storage`-event adoption in the second context |
| `a legacy character set` | Percent-encoded cp1251 in the query string, which `URLSearchParams` decodes to U+FFFD |
| `the browser holds no campaign parameters` | The frozen-UTM storage key is absent — nothing written, not written-then-emptied |
| `behaves as it does for a visitor arriving with no parameters` | Asserted against that load: same rendered page, no banner, no console error, `SITE_VISITED` still reported |
| `recovers through the offered action` | The editor's own `ErrorBoundary` recovery target |
