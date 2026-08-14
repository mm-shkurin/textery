<!-- COPIED FILE. Source of truth: ProductSpecification/stories/12-my-projects/tests/extended/02_UI_Tests_Extended.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — UI Tests (Extended)

---

## 1. Layout

### 1.1 The grid collapses to one column on a phone
```gherkin
Given a phone-sized viewport
When the user opens «Мои проекты»
Then the cards are shown one per row
And no horizontal scrolling is needed
```

### 1.2 A long project title is truncated without breaking the card layout
```gherkin
Given a project whose title is far longer than the card
When the feed is rendered
Then the title is truncated within the card bounds
```

### 1.3 Both source kinds are visually distinguishable
```gherkin
Given the user owns a document and a failed generation
When they open «Мои проекты»
Then the two cards are told apart without reading their text
```

---

## 2. Search and Sort

### 2.1 Clearing the search restores the recent-projects section
```gherkin
Given an active search
When the user clears the query
Then the full feed is shown again
And the recent-projects section reappears
```

### 2.2 The recent section under an active search
```gherkin
Given the user has searched
When results are shown
Then the recent section behaves as the story pins it
```

### 2.3 The result count updates as the query narrows
```gherkin
Given an active search returning several results
When the user extends the query so fewer match
Then the displayed result count matches the returned results
```

### 2.4 Pressing Enter in the search field does not submit a page reload
```gherkin
Given focus in the search field
When the user presses Enter
Then the feed updates in place without a full page reload
```

### 2.5 Sorting is reachable by keyboard
```gherkin
Given the user is on «Мои проекты»
When they reach the sort control by keyboard alone
Then they can change the order without a mouse
```

### 2.6 An empty search result keeps the sort selection visible
```gherkin
Given a non-default sort and a query matching nothing
When the empty state is shown
Then the chosen sort is still displayed
```

---

## 3. Retry

### 3.1 The retry button is disabled while its request is in flight
```gherkin
Given the user clicked retry on a failed generation
When the request has not yet returned
Then the button is disabled
```

### 3.2 The retry action is absent on an unknown status
```gherkin
Given a project whose status the app does not recognise
When the user opens «Мои проекты»
Then its card offers no retry action
```

### 3.3 A retry shows progress until it resolves
```gherkin
Given the user retries a failed generation
When the new generation is still running
Then its card shows that it is in progress
```

---

## 4. Restored State

### 4.1 The chosen view survives a reload
```gherkin
Given the user switched to list view
When the user reloads the page
Then the feed is still rendered as a list
```

### 4.2 The page number survives a return from the editor
```gherkin
Given the user is on a later page of their projects
When they open a project and navigate back
Then the same page is shown
```

### 4.3 A shared link reproduces the same filtered feed
```gherkin
Given a feed narrowed by search and sort
When the same address is opened afresh
Then the same query, order, and page are shown
```

---

## 5. Inert Controls

### 5.1 Inert controls do not navigate
```gherkin
Given the category filters and the actions menu are shown as unavailable
When the user clicks them
Then nothing is navigated and no request is sent
```

---

## DSL Technical Reference

Inherits `02_UI_Tests.md`.
