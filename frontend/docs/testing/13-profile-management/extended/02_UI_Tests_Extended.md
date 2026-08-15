<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/extended/02_UI_Tests_Extended.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Profile management — UI Tests (Extended)

---

## 1. Layout and Presentation

### 1.1 The profile screen holds its single-column shell width
```gherkin
Given a signed-in user on a desktop viewport
When they open the profile screen
Then the content sits within the single-column page width
And it is not laid out at the project feed's width
```

### 1.2 The screen is usable on a narrow viewport
```gherkin
Given a signed-in user on a narrow viewport
When they open the profile screen
Then the identity, the name field and both buttons are all reachable without horizontal scrolling
```

### 1.3 A very long name does not break the header
```gherkin
Given a signed-in user whose name is the bound's worth of characters
When any authenticated page renders
Then the header keeps its layout
And the name is truncated visually rather than overflowing
And the full name is shown on the profile screen
```

---

## 2. Menu Behaviour

### 2.1 The avatar menu dismisses without navigating
```gherkin
Given a signed-in user with the avatar menu open
When they click outside the menu
Then the menu closes
And the page does not change
```

### 2.2 «Мой профиль» is offered while the header is degraded
```gherkin
Given a signed-in user whose profile read has failed
When they open the avatar menu
Then «Мой профиль» is offered
When they choose it
Then the profile screen opens in its load-failed state
```

*Either the item survives the degraded state deliberately or it is hidden; drifting into
one of the two is what this pins (`13_ProfileManagement_Notes.md` § UI/UX Warnings).*

---

## 3. Field Behaviour

### 3.1 The counter reads zero on an empty field
```gherkin
Given a signed-in user whose profile carries no name
When they open the profile screen
Then the counter reports nothing typed
And it does not report the value as over the limit
```

### 3.2 Cancelling restores the saved value
```gherkin
Given a signed-in user who changed the name field without saving
When they cancel
Then the field holds the saved name again
And nothing is reported as unsaved
```

### 3.3 Pasting an over-long name is reported, not silently truncated
```gherkin
Given a signed-in user on the profile screen
When they paste a name past the bound
Then the counter marks the value as over the limit
And the pasted text is still in the field
And saving is not offered
```

---

### 3.4 An unrenderable registration date announces itself
```gherkin
Given a signed-in user whose registration date cannot be read
When they open the profile screen
Then the placeholder dash is shown
And the failure is reported to the product's client-side error channel naming the field
Given a signed-in user whose registration date is well formed
Then no such failure is reported
```

*The dash is a fallback rendering as ordinary data — indistinguishable from a legitimately
dashed value, and silent about a serializer that started producing garbage.*

---

## 4. Avatar

### 4.1 Initials follow the name once it is set and the address when it is cleared
```gherkin
Given a signed-in user whose profile carries no name
Then the avatar shows initials derived from the address
When they save a two-word name
Then the avatar shows initials derived from that name
When they clear the name
Then the avatar shows initials derived from the address again
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the single-column page width` | 1240px shell (`ProductSpecification/ui/ui-conventions.md`) |
| `the project feed's width` | 1640px shell of story 12 |
| `the bound` | 60 code points |
| `the counter` | Client-side code-point counter on the name field |
| `nothing is reported as unsaved` | `useUnsavedGuard` dirty flag cleared |
