<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/06_Integration_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Profile management — Integration Tests

**No external service is involved.** The seam this story creates is internal and new: the
application shell gains a hard dependency on a backend route that did not exist, on every
authenticated page. Before this story a profile-endpoint outage was not a concept; after it,
one degrades the whole authenticated shell at once
(`13_ProfileManagement_Notes.md` § Integration Notes). These scenarios exercise the browser
against a live backend through the real origin — not stubs.

---

## 1. The Screen Against a Live Backend

### 1.1 A name saved in the browser is the name the backend stored
```gherkin
Given a user signed in through the application against a live backend
When they open their profile, type a name and save
Then the screen shows the saved name
And reading the profile back from the backend returns that same name
And signing in again in a fresh browser session shows that name in the header
```

### 1.2 A name with astral characters survives the whole round trip
```gherkin
Given a user signed in through the application against a live backend
When they save a name of the bound's worth of astral characters
Then the save succeeds
And the name is shown character for character on the screen and in the header
And reading the profile back from the backend returns it unchanged
```

*The counter, the domain bound and the column each count a different unit if anyone gets it
wrong; only the whole round trip catches a mismatch between them.*

### 1.3 Clearing a name in the browser clears it in the backend
```gherkin
Given a user signed in through the application whose profile carries a name
When they empty the name field and save
Then the screen and the header fall back to the address
And reading the profile back from the backend reports no name
```

### 1.4 An oversized save is refused through the origin the browser uses
```gherkin
Given a user signed in through the application against a live backend
When a save far exceeding the request body cap is sent through the application's origin
Then it is refused for size in this product's canonical failure form
And the refusal is not the proxy's own HTML error page
And the failed-save screen is shown
```

---

## 2. Ordering Across the Seam

### 2.1 A stale profile read never overwrites a completed rename
```gherkin
Given a user signed in through the application whose profile read is held open
When they save a new name and the save completes first
Then the header and screen show the new name
When the held profile read then arrives with the old name
Then the header and screen still show the new name
```

### 2.2 An out-of-order rename response never wins
```gherkin
Given a user signed in through the application
When they save one name and then another before the first response arrives
And the second response arrives first
Then the screen shows the second name
And it still shows the second name after the first response arrives
```

### 2.2a A superseded profile read never repaints the header
```gherkin
Given a user signed in through the application whose profile read is held open
When the read is retried — by the user and by the retry policy in turn — and the retry answers first
Then the header and the profile screen show the retry's identity
And they still show it after the superseded read finally arrives
```

*Every other ordering scenario pairs a read with a write, a write with a write, or a read
across a session boundary. Read-versus-read is created by this spec's own retry paths and is
the case where a stale or degraded result repaints a healthy header.*

### 2.3 An identity from a superseded session is dropped
```gherkin
Given a user whose profile read is held open
When they sign out and sign in as a different account in the same tab
And the held response for the first account then arrives
Then the header shows the second account's identity
And it is never replaced by the first account's
```

---

## 3. Degradation of the Seam

### 3.1 A failing profile endpoint degrades the shell without ending the session
```gherkin
Given a user signed in through the application
When the profile endpoint starts failing as a server fault
Then every authenticated page still renders with a degraded identity
And «Выйти» still ends the session
And the stored session survives until the user ends it
```

### 3.2 A slow profile endpoint is abandoned rather than waited on forever
```gherkin
Given a user signed in through the application
When the profile endpoint stops answering
Then the read is abandoned once its bounded wait elapses
And the header shows its degraded identity rather than the loading placeholder forever
```

### 3.3 Retries after an outage are capped and spread out
```gherkin
Given a user signed in through the application
When the profile endpoint fails repeatedly and then recovers
Then the number of retries is capped
And successive attempts are spaced with growing, varied delays
And the identity appears once the endpoint recovers
```

*Every open tab in the fleet re-reads this endpoint at boot, so retries in lockstep after a
rolling deploy are a self-inflicted load spike on the endpoint that just came back.*

### 3.3a A save is never re-sent on its own, and a manual retry stores one name
```gherkin
Given a user signed in through the application
When a save's response never arrives and its bounded wait elapses
Then no rename is re-sent automatically
And the failed-save screen is shown with the typed name intact
When the user retries and the first attempt had in fact committed
Then reading the profile back from the backend returns the submitted name
And exactly one account row exists for them
```

*The read's retry policy must not extend to the write. This is the direction the re-run
guards in the API file do not reach: they cover a duplicate the caller sends deliberately,
not one a client policy sends on its behalf after an ambiguous outcome.*

### 3.3b A save the client abandons does not leave the screen lying
```gherkin
Given a user signed in through the application
When a save's response is delayed past the client's bounded wait and the server commits anyway
Then the abandoned request is cancelled at the client
And the identity shown never claims a value the server did not store
And the next profile read reconciles the screen to the stored name
```

### 3.3c A non-JSON answer from the proxy degrades rather than breaks
```gherkin
Given a user signed in through the application
When the profile read answers with the proxy's own HTML error page
Then every authenticated page still renders with the degraded identity
And «Выйти» still ends the session
And no parsing failure escapes into the shell
```

*3.4 covers a body that is valid JSON with fields missing. The proxy's own 502 and 504 pages
during a rolling deploy are not JSON at all, and that is the shape the whole fleet sees at
once.*

### 3.4 A malformed profile body does not break the shell
```gherkin
Given a user signed in through the application
When the profile endpoint answers successfully with fields missing
Then every authenticated page still renders
And no undefined value reaches the avatar's initials
And «Выйти» still ends the session
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `signed in through the application` | Selenium drives the real sign-in flow; no injected session |
| `against a live backend` | Acceptance stack: browser → nginx → FastAPI → Postgres |
| `the application's origin` | `app_url` (through `infra/docker/nginx/frontend.conf`), never `BACKEND_PORT` |
| `reading the profile back from the backend` | Direct `GET /api/v1/auth/me` with the same account's token |
| `the profile read is held open` | Response delayed at the test double / proxy until released |
| `the bound` | 60 code points |
| `astral characters` | U+1F600 — 1 code point, 2 UTF-16 units, 4 UTF-8 bytes |
| `this product's canonical failure form` | `{"error_code": …, "message": …}` |
| `its bounded wait` | The client-side timeout on the shared profile fetch |
| `the stored session survives` | Session key still present; `clearSession()` not reached |
