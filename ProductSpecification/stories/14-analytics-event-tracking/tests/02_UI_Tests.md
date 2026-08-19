> **Implementation Order**: sequential TDD — mint and reuse the visitor identity → freeze
> attribution → emit from the three browser surfaces → degrade without showing it → clean up
> after account deletion.

# Analytics Event Tracking — UI Tests

**This story renders nothing.** There is no screen, no button and no message to assert on, so
these scenarios assert what the browser *does*: which identity it carries, what it froze, what
it sent, and — as much as anything here — what it never shows the user.

> **Navigation is by clicking, never by typing a URL** (`.claude/guidelines/frontend-rules.md`).
> Where a scenario needs a marketing link, that is the initial page load, which is the one
> navigation a visitor really performs from outside.

> **«Invisible to the visitor» is half the requirement.** A client that retries forever, or
> that silently signs the user out on a telemetry refusal, satisfies every «nothing appears on
> screen» assertion. Section 4 asserts both halves: what the visitor never sees, and what the
> operator must still be able to see.

---

## 1. Visitor Identity

### 1.1 A first-ever visitor is given an identity before anything is reported
```gherkin
Given a browser that has never visited the site
When the visitor opens the landing page
Then the browser holds a stored visitor identity
And the reported site visit carries that same identity
```

### 1.2 A returning visitor keeps the identity it already had
```gherkin
Given a browser that already holds a visitor identity
When the visitor opens the landing page again
Then the stored identity is unchanged
And the reported site visit carries it
```

### 1.3 A stored identity that is not well-formed is replaced, not reused
```gherkin
Given a browser holding a stored visitor identity that is not well-formed
When the visitor opens the landing page
Then the browser holds a different, well-formed identity
And the reported site visit is accepted
```

### 1.4 Signing in does not change the visitor identity
```gherkin
Given a visitor holding an identity who opens the landing page
When the visitor signs in
And it opens a document in the editor
Then the reported editor opening carries the same identity as the site visit
And that event is also attributed to the signed-in account
```

---

## 2. First-Touch Attribution

> **The freeze is best-effort and silent.** Nothing in this section may block, delay or show
> anything to the visitor: campaign parameters that cannot be read or cannot be stored are
> simply not frozen, the page behaves exactly as it does for a visitor arriving with no
> parameters, and a later readable link can still become the first touch. Those two cases are
> owned by `extended/02_UI_Tests_Extended.md` §2.1 and §2.2, and by the Governing Decision in
> `14_AnalyticsEventTracking.md`.

### 2.1 The first visit carrying campaign parameters freezes them
```gherkin
Given a browser that has never visited the site
When the visitor arrives from a link carrying campaign parameters
Then the browser holds those campaign parameters
```

### 2.2 A later visit from a different campaign does not overwrite the first
```gherkin
Given a browser holding frozen campaign parameters
When the visitor arrives from a link carrying different campaign parameters
Then the browser still holds the first set
```

### 2.3 A visit with no campaign parameters leaves the browser open to a later first touch
```gherkin
Given a browser that has never visited the site
When the visitor arrives with no campaign parameters
Then the browser holds no campaign parameters
When the visitor later arrives from a link carrying them
Then the browser holds that set
```

### 2.4 Registration carries the frozen set, not the current address
```gherkin
Given a browser holding frozen campaign parameters
When the visitor navigates within the site until the campaign parameters are no longer in the address
And it registers
Then the created account carries the frozen campaign parameters
```

### 2.5 Multibyte campaign parameters survive the freeze unchanged
```gherkin
Given a marketing link whose campaign parameters combine Cyrillic text and characters outside the basic plane
When the visitor arrives from it
And it navigates within the site until the parameters are no longer in the address
And it registers
Then the created account carries those parameters byte-identical to the link, after normalization
```

The server half of this round trip is covered. The client half — percent-decode, serialize
into storage, read back, put in the request body — crosses three encode/decode boundaries and
had no fixture with any character content specified.

---

## 3. What the Browser Reports

### 3.1 One page load reports exactly one site visit
```gherkin
Given a visitor opening the landing page
When the page has finished loading
Then exactly one site visit is reported
```

### 3.2 Reaching the registration screen reports it once
```gherkin
Given a visitor on the landing page
When it follows the call to action to the registration screen
Then exactly one registration start is reported
When it leaves for the sign-in screen and returns to registration
Then the number of reported registration starts matches the number of times the screen was reached
```

### 3.3 Opening a document in the editor reports it once
```gherkin
Given a signed-in account holding a document
When it opens that document from its project list
Then exactly one editor opening is reported for that document
```

### 3.4 Opening a document twice in one gesture reports one opening
```gherkin
Given a signed-in account holding a document
When it activates that document twice in rapid succession without waiting for the first to open
Then exactly one editor opening is recorded for that document
And the control behaves exactly as it does today, gaining no disabled or busy state
```

Every other duplicate-suppression scenario here is mount-driven. Two rapid activations are two
distinct open-intents, and if each mints its own occurrence key the server-side collapse cannot
help — there is nothing to collapse.

**Revised 2026-08-19.** The scenario previously demanded «the control is inert while the first
opening is in flight». Opening a document is a synchronous state transition today
(`useFlowNavigation.openDocumentFromHistory`); nothing is «in flight» and no control has a busy
state. Adding one would be a UX change made to suit an event, which this story does not do
(Governing Decision §6 and §8). The dedupe belongs in how the emitter derives its occurrence —
from the opening itself — not in new UI state, and the second assertion is now what keeps an
implementer from reaching for the disabled prop.

### 3.5 Moving within the site reports no further site visit
```gherkin
Given a visitor who has opened the landing page
When it follows the call to action to the registration screen
And it returns to the landing page through the browser's back control
Then exactly one site visit is recorded in total
```

The rule is stated in `interview.md` and the whole occurrence-key design rests on «one event
per page load». If the emitter hangs off a route effect rather than the app mount, a back
navigation re-mounts it with a *fresh* key, the collapse never fires, and every funnel's
denominator inflates silently.

### 3.6 Two reports on the wire together keep their dispatch order
```gherkin
Given a visitor whose site visit report is still in flight
When it reaches the registration screen and that report is sent before the first has answered
And the first report's answer arrives after the second's
Then both events are recorded for that visitor
And read in order, the site visit is returned before the registration start
```

The order key is assigned on **arrival**, so arrival order is the wrong order when the second
send wins the race. This scenario is what forces the design decision — dispatch-ordered
emission, or a client-carried ordinal — rather than leaving the funnel to read backwards.

---

## 4. Degrading Without Showing It

### 4.1 A browser that cannot store still reports, and says so in the data
```gherkin
Given a browser whose storage refuses to be written
When the visitor opens the landing page
Then a site visit is still reported
And the reported event is marked as coming from a browser that could not store its identity
And nothing on the page tells the visitor anything went wrong
```

### 4.2 Two loads from a browser that cannot store are two different visitors
```gherkin
Given a browser whose storage refuses to be written
When the visitor opens the landing page twice
Then the two reported site visits carry different identities
```

### 4.3 An unreachable analytics endpoint is invisible to the visitor
```gherkin
Given the analytics endpoint refuses every request
When the visitor opens the landing page
And it registers, signs in and opens a document in the editor
Then every screen behaves exactly as it does normally
And no error, banner or spinner appears anywhere
```

### 4.4 A visitor who leaves immediately is still counted
```gherkin
Given a visitor opening the landing page
When the visitor leaves the page immediately after it loads
Then the site visit still reaches the server
```

### 4.5 An analytics endpoint that never answers blocks nothing
```gherkin
Given the analytics endpoint accepts requests and never answers them
When the visitor opens the landing page, reaches registration and opens a document in the editor
Then every screen renders and accepts input with no additional delay
And no spinner, banner or error appears at any point
And the product's own requests are not delayed behind the unanswered reports
When one report hangs and the next is issued
Then the later report is still sent
```

The spec names three client states — «slow, failing or unreachable». 4.3 stubs only the fast
ones. A hang is the state that holds one of the browser's few per-host connections, starving
the product's own calls, and that a naive await turns into a delayed route transition.

### 4.6 Every refusal from the analytics endpoint is inert in the browser
```gherkin
Given a signed-in visitor working in the editor with unsaved changes
When its reports are refused as unauthorized
And its reports are refused as rate limited
And its reports are refused as invalid
Then the visitor remains signed in and on the same screen
And its unsaved changes are still present
And no error, banner or spinner appears
And no report is retried
```

The concrete incident: a signed-in user's token expires mid-editing, the analytics call
returns unauthorized, and — if the emitter shares the product's HTTP client and that client
has or later gains a global sign-out-on-401 handler — an invisible telemetry call logs the
user out of the editor and discards their unsaved content. This scenario pins the exemption
rather than leaving it to the emitter happening to use a bare fetch today.

### 4.7 Each send-failure family is counted, and a success is not
```gherkin
Given the analytics endpoint failing by timeout, by refusal and by network error in turn
When the visitor opens the landing page under each
Then each records exactly one attempt and no retry
And nothing is held in the browser awaiting a later attempt
And each increments a distinguishable drop signal
And a successful send increments nothing
When the endpoint becomes reachable again
And the visitor opens a document in the editor
Then exactly one request is issued, carrying only that opening
```

Two requirements in one scenario because they fail together: without the attempt-count half a
recovering backend meets every visitor's backlog at once, and without the drop-signal half a
broken ingest route looks byte-identical to a quiet day. The repo already ships a four-attempt
retry policy for autosave — the precedent an implementer will copy.

---

## 5. After Account Deletion

### 5.1 Deleting the account clears the identity and the frozen attribution
```gherkin
Given a signed-in account in a browser holding a visitor identity and frozen campaign parameters
When it deletes its account
Then the browser holds neither a visitor identity nor campaign parameters
When the visitor opens the landing page again
Then the browser holds a different visitor identity
```

### 5.2 Deleting the account leaves the visitor's other preferences alone
```gherkin
Given a signed-in account in a browser with a chosen colour theme
When it deletes its account
Then the chosen theme is still in effect
```

### 5.3 A registration after a deletion is not attributed to the deleted account's campaign
```gherkin
Given a browser whose account registered from a campaign link and has since been deleted
When a new account registers from that browser with no campaign parameters
Then the new account carries no campaign parameters
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the browser holds a stored visitor identity` | Namespaced `localStorage` key read through `readStored('local', …)` |
| `not well-formed` | A stored value that does not parse as a UUID |
| `arrives from a link carrying campaign parameters` | Initial page load with `?utm_source=…&utm_campaign=…` |
| `the browser holds those campaign parameters` | Namespaced `localStorage` key holding the frozen set |
| `characters outside the basic plane` | Astral-plane code points, asserted byte-exact end to end |
| `navigates within the site` | In-app flow transitions — never a typed URL |
| `exactly one site visit is reported` | One `POST /api/v1/analytics/events` with `SITE_VISITED`, asserted under `<StrictMode>` as `main.tsx` mounts it |
| `activates that document twice in rapid succession` | Two clicks with no await between them, against the control exactly as it renders today |
| `gaining no disabled or busy state` | The control's rendered props are unchanged from the pre-story component — no `disabled`, no `aria-busy` added for the emitter's benefit |
| `the browser's back control` | History navigation, not an in-app link |
| `recorded in total` | Counted on stored rows, so the server-side collapse cannot satisfy the assertion |
| `storage refuses to be written` | `localStorage` stubbed to throw, as in private-mode Safari |
| `marked as coming from a browser that could not store` | `degraded: true` on the event body |
| `the analytics endpoint refuses every request` | Route stubbed to 5xx / network failure |
| `accepts requests and never answers them` | Route stubbed to hang past the client's own deadline |
| `refused as unauthorized / rate limited / invalid` | 401, 429 and 400 from the events route |
| `a distinguishable drop signal` | A client-side counter or log distinct per failure family, readable without the visitor seeing it |
| `leaves the page immediately` | Trigger unload right after load; the send must use the beacon/keepalive path |
| `the chosen colour theme` | The `theme` key in `localStorage` (`shared/theme/theme.ts`) |
| `deletes its account` | The existing deletion flow on the profile screen |
