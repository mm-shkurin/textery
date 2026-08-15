> These are additional edge case tests. Implement after core tests pass.

# Profile management — Integration Tests (Extended)

No external service. These extend the internal browser-to-backend seam covered in the main
file.

---

## 1. Multiple Surfaces on One Session

### 1.1 A rename in one tab is seen by another after it re-reads
```gherkin
Given a user signed in through the application in two tabs
When they rename themselves in the first tab
And the second tab loads an authenticated page afterwards
Then the second tab shows the new name
```

### 1.1a The staleness window on another surface is the one this contract states
```gherkin
Given a user signed in through the application in two tabs
When they rename themselves in the first tab
Then the second tab may show the previous name until its next full page load
And it shows the new name from that load onwards
And it never shows the previous name after one
```

*The identity snapshot is fetched once per page and never refreshed within it (main UI file
6.4, 6.7), so a second surface is stale for an unbounded time by design. 1.1 asserts only
that it eventually catches up, which lets any lag pass; this names the single refresh point
that the design actually has.*

### 1.2 Browser history navigation does not resurrect a stale identity
```gherkin
Given a user signed in through the application who renamed themselves
When they navigate back and then forward through the browser's own history
Then every page shows the new name
```

---

## 2. Session Transitions Against a Live Backend

### 2.1 Signing in as another account replaces the identity everywhere
```gherkin
Given a user signed in through the application whose profile carries a name
When they sign out and sign in as a different account in the same tab
Then the header and the profile screen show the second account's identity
And nothing on the page carries the first account's address or name
```

### 2.2 An expired access token is renewed without disturbing the identity
```gherkin
Given a user signed in through the application whose access token has expired
When an authenticated page loads and the profile is read
Then the session is renewed
And the header shows the account's identity
And the user is not returned to the sign-in screen
```

---

## 3. Registration Date End to End

### 3.1 The date shown is the instant the account was created
```gherkin
Given an account registered through the application at a known instant
And a browser running in a timezone other than UTC
When the user opens their profile screen
Then the registration date shown is that instant's date
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `signed in through the application` | Selenium drives the real sign-in flow against the acceptance stack |
| `an authenticated page` | Any route behind the session guard, all of which mount the header |
| `the session is renewed` | Refresh flow in `authorizedRequest.ts` |
| `a timezone other than UTC` | Browser/session `TZ` pinned away from UTC |
