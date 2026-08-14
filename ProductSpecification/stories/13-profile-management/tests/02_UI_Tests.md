> **Implementation Order**: sequential TDD — the menu entry and the route → the screen's
> read states → typing and the length counter → submission → validation feedback → server
> response and the header → the degraded header contract → navigation and unsaved input.

# Profile management — UI Tests

Screen: `/profile`. Mockups: `mockups/desktop/01`–`08` and their mobile twins. The
**save-failed** state (`13_ProfileManagement.md` § Screen States) has no mockup — these
scenarios are its definition.

> **The header is on every authenticated page.** Section 6 is therefore not "profile screen"
> coverage: it fixes what the whole application shell renders while `/me` is in flight,
> failing, or answering nonsense.

---

## 0. Prerequisite Guard

### 0.1 The profile route is not reachable without a session
```gherkin
Given a visitor with no session
When they open the profile screen directly
Then they are taken to the sign-in screen
And no identity is rendered anywhere on the page
```

---

## 1. Entering the Screen

### 1.1 The avatar menu offers «Мой профиль» above «Выйти»
```gherkin
Given a signed-in user on any authenticated page
When they open the avatar menu
Then «Мой профиль» is offered
And it sits above «Выйти»
And the address row in the menu is still not interactive
```

### 1.2 «Мой профиль» navigates to the profile screen
```gherkin
Given a signed-in user with the avatar menu open
When they choose «Мой профиль»
Then the profile screen opens
And the avatar menu closes
```

---

## 2. Reading the Profile

### 2.1 The screen shows a defined placeholder while the profile is in flight
```gherkin
Given a signed-in user whose profile has not yet answered
When they open the profile screen
Then a defined loading placeholder is shown for the identity and the avatar
And no empty avatar is shown that later pops into initials
```

### 2.2 A profile with a name shows the name, the email and the registration date
```gherkin
Given a signed-in user whose profile carries a name
When they open the profile screen
Then the name is shown in the name field
And the registered address is shown
And the registration date is shown in this product's date form
```

### 2.3 A profile with no name shows the email as the identity and an empty field
```gherkin
Given a signed-in user whose profile carries no name
When they open the profile screen
Then the name field is empty
And the registered address is shown as the identity
And the avatar shows initials derived from the address
```

### 2.4 The registration date renders through the product's existing date formatter
```gherkin
Given the browser is running in a timezone other than UTC
And a signed-in user whose registration instant is known
When they open the profile screen
Then the registration date reads as that instant's date in this product's date form
And an unparseable registration date renders as the product's placeholder dash
```

### 2.3a The registration date always carries its year
```gherkin
Given a signed-in user who registered in the current calendar year
When they open the profile screen
Then the registration date shows the year
Given a signed-in user who registered in an earlier year
When they open the profile screen
Then the registration date shows that year
```

*Decided here rather than inherited: the shared card formatter hides the year when it matches
the current one, which is right for a feed of recent work and wrong for "с нами с …" — a
date with no year answers a different question than the one the row asks. The formatter needs
a flag; the alternative, accepting the hiding, was rejected.*

### 2.4a The date shown is the local calendar date, at the boundary where that differs
```gherkin
Given a registration instant half an hour before midnight UTC
And a browser in a timezone ahead of UTC
When the user opens the profile screen
Then the date shown is the following calendar day
Given a registration instant half an hour after midnight UTC
And a browser in a timezone behind UTC
When the user opens the profile screen
Then the date shown is the preceding calendar day
```

*2.4 leaves the instant unspecified, so it stays green against the classic defect — a date
bucketed on raw UTC — which is only observable within the zone offset of midnight.*

### 2.4b The screen holds its form under a hostile locale
```gherkin
Given a browser locale whose casing and number rules differ from the default
When a signed-in user opens the profile screen
Then the registration date reads in this product's date form
And the counter reports the same value as under the default locale
And the initials derived from the address are the same as under the default locale
```

*Dotted-I casing and comma decimals both reach this screen — through the initials and
through the counter — and neither is visible in any other scenario.*

### 2.5 A failed profile read offers a retry, not a perpetual spinner
```gherkin
Given a signed-in user whose profile read fails
When they open the profile screen
Then a failure message is shown
And a retry affordance is offered
When they retry and the read succeeds
Then the profile is shown
```

---

## 3. Typing a Name

### 3.1 Save is inert until the typed value differs from the saved one
```gherkin
Given a signed-in user on the profile screen with a saved name
Then saving is not offered
When they change the name
Then saving is offered
When they restore the original value
Then saving is not offered again
```

### 3.2 The length counter counts what the server counts
```gherkin
Given a signed-in user on the profile screen
When they type a name of the bound's worth of astral characters
Then the counter reads the bound as reached, not exceeded
And saving is offered
When they type one character more
Then the counter marks the value as over the limit
And saving is not offered
```

### 3.3 The counter and the changed-flag judge the normalized value
```gherkin
Given a signed-in user on the profile screen
When they type a name written as base and combining pairs that normalizes to the bound
Then the counter reads the bound as reached, not double it
And saving is offered
```

---

## 4. Saving

### 4.1 Saving shows a working state and refuses a second submission
```gherkin
Given a signed-in user who has changed their name
When they save and the response has not yet arrived
Then the form reports that it is saving
And the form cannot be submitted again until the response arrives
```

### 4.2 A double click and a double Enter each save once
```gherkin
Given a signed-in user who has changed their name
When they click save twice in quick succession
Then exactly one rename is sent
When they press Enter twice in quick succession
Then exactly one rename is sent
```

### 4.3 A successful save leaves nothing unsaved
```gherkin
Given a signed-in user who typed a name with a trailing space
When they save and the rename succeeds
Then the field holds the value the server stored
And nothing is reported as unsaved
```

### 4.4 Clearing the name falls back to the address everywhere
```gherkin
Given a signed-in user whose profile carries a name
When they empty the name field and save
Then the screen shows the address as the identity
And the avatar shows initials derived from the address
```

---

## 5. Validation and Save Failure

### 5.1 A refused name is reported inline and the typed value survives
```gherkin
Given a signed-in user on the profile screen
When they save a name the server refuses as invalid
Then the reason is shown beside the name field
And the field still holds what they typed
And the identity shown elsewhere on the screen is unchanged
```

### 5.2 A failed save blames the attempt, not the input
```gherkin
Given a signed-in user who has changed their name
When the save fails as a server fault
Then a failure banner is shown over the filled card
And a retry affordance is offered
And the typed name is still in the field
And the form is interactive again
When they retry and the save succeeds
Then the banner is gone and the new name is shown
```

### 5.3 A refused name and a failed save are told apart
```gherkin
Given a signed-in user on the profile screen
When a save is refused as invalid
And a later save fails as a server fault
Then the two produce visibly different screens
And neither is reported as the other
```

### 5.3a A refusal this client version does not know falls to the defined default
```gherkin
Given a signed-in user on the profile screen
When a save is refused with a failure code this client version does not define
Then the failed-save screen is shown with the typed name intact
And the refusal is not reported as an invalid name beside the field
And the screen neither blanks nor crashes
```

*The two sides deploy independently, so the backend emitting a code the shipped bundle does
not define is a routine deploy state, not an exotic one. The default branch of a failure-code
switch is exactly where a screen silently mislabels or dies.*

### 5.4 A save refused for body size is reported as a failed save
```gherkin
Given a signed-in user on the profile screen
When a save is refused for size at the transport boundary
Then the failed-save screen is shown, not a blank one
And the typed name is still in the field
```

---

## 6. The Header Across `/me` States

### 6.1 Each profile state has its own defined header
```gherkin
Given a signed-in user on any authenticated page
When the profile read is in flight
Then the header shows the loading placeholder
When the profile read fails
Then the header shows a degraded identity
And the degraded identity is visibly distinct from the loading placeholder
When the profile answers with fields missing
Then the header renders without crashing
And no undefined value reaches the initials
```

### 6.1a A profile answering with an unknown extra field renders normally
```gherkin
Given a signed-in user on an authenticated page
When the profile read answers with the defined fields plus one this client version does not know
Then the identity renders exactly as it would without that field
And the body is not treated as malformed
```

*6.1 covers only the missing-field direction. The response is expected to grow — the
verification status is excluded today by decision, not permanently — and during any rolling
deploy the old bundle reads the new body.*

### 6.2 «Выйти» works in every profile state
```gherkin
Given a signed-in user on any authenticated page
When the profile read is in flight, has failed, and answered unauthorized in turn
Then «Выйти» is offered in each case
And choosing it ends the session in each case
```

### 6.3 A failing profile read never signs the user out
```gherkin
Given a signed-in user on an authenticated page
When the profile read fails as a server fault
And when it times out
And when it is refused as unauthorized and the renewal then fails
Then the stored session survives each case
And the user is not returned to the sign-in screen
```

### 6.4 One profile read per page, not one per header
```gherkin
Given a page mounting two avatar menus
When the page loads
Then exactly one profile read is issued
When the user navigates to another authenticated page in the application
Then no further profile read is issued
```

### 6.5 Both mounted menus agree in every state
```gherkin
Given a page mounting two avatar menus
When the shared profile read fails
Then both menus show the same degraded identity
```

### 6.6 A rename updates every mounted header without a reload
```gherkin
Given a signed-in user on the profile screen with a second header mounted
When they save a new name
Then every mounted header shows the new name
And no page reload occurs
And no second profile read is issued
```

### 6.7 The identity survives in-app navigation and is not refetched
```gherkin
Given a signed-in user who has just renamed themselves
When they navigate away within the application and back
Then the new name is still shown
And no further profile read is required to show it
```

### 6.8 Initials never split a character
```gherkin
Given a signed-in user whose name begins with an astral character
Then the avatar shows one whole character
Given a signed-in user whose name begins with a base and combining pair
Then the avatar shows one whole character
And in neither case is a replacement character shown
```

---

## 7. Navigation and Unsaved Input

### 7.1 Leaving with a typed but unsaved name is guarded
```gherkin
Given a signed-in user who typed a name and did not save
When they navigate away within the application
Then they are asked to confirm leaving
And the prompt names this screen, not the registration screen
When they cancel
Then they stay on the profile screen with the typed value intact
```

### 7.2 A reload with a typed but unsaved name does not lose it silently
```gherkin
Given a signed-in user who typed a name and did not save
When they reload the page
Then the browser warns before leaving
```

### 7.3 A header profile failure mid-edit does not drop the typed name
```gherkin
Given a signed-in user typing a name on the profile screen
When the header's profile read is refused as unauthorized
Then the typed name is still in the field
And the user is not returned to the sign-in screen
```

### 7.3a Signing out with a typed but unsaved name is guarded like any other exit
```gherkin
Given a signed-in user who typed a name on the profile screen and did not save
When they choose «Выйти»
Then they are asked to confirm before the session ends
When they cancel
Then they stay on the profile screen with the typed value intact
And the session is untouched
```

*«Выйти» is mounted on this page like every other, which makes it a third exit over the same
dirty state. 7.1 guards in-app navigation and 7.2 guards reload; 6.2 pins that sign-out always
works, and the two together currently imply silent loss.*

### 7.3b A save refused as unauthorized does not discard the typed name silently
```gherkin
Given a signed-in user who typed a name and saved
When the save is refused as unauthorized and the renewal then fails
Then the typed value is still available to the user after the session ends
Or its loss is announced before the session ends
And it is not discarded by an unannounced return to the sign-in screen
```

*6.3 deliberately keeps a failing **read** from ending the session; the write path is the one
the interceptor still owns, and it is where typed text is standing on the screen.*

### 7.4 Save and cancel are reached in that order by keyboard
```gherkin
Given a signed-in user on the profile screen on a narrow viewport
When they move through the form with the keyboard
Then the reading order matches the visual order of the buttons
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a signed-in user` | Session in `sessionStorage` + stubbed `GET /api/v1/auth/me` |
| `the profile screen` | Route `/profile` |
| `the avatar menu` | `ProfileMenu` in `AppHeader` |
| `the profile read` | `GET /api/v1/auth/me` from the shared identity fetch |
| `a rename` / `they save` | `PATCH /api/v1/auth/me` |
| `the bound` | 60 code points |
| `astral characters` | U+1F600 — `.length` counts 2 per character, the counter must not |
| `this product's date form` | `formatCardDate` (ru-RU genitive month, `—` on unparseable); test `TZ` pinned to a non-UTC zone |
| `the degraded identity` | Dashed-outline avatar state of `08-header-degraded.html`, asserted distinct from the loading placeholder |
| `nothing is reported as unsaved` | `useUnsavedGuard` dirty flag cleared, compared against the normalized server value |
| `they are asked to confirm leaving` | `useUnsavedGuard` `confirmLeave`, message parameterized per screen |
| `exactly one profile read is issued` | Request count against the stubbed endpoint, both `ProfileMenu` instances mounted |
| `the stored session survives` | `clearSession()` not reached; session key still present |
