> **Implementation Order**: sequential TDD — feed display → view toggle → search →
> sort → retry → state persistence → empty and error states.

# Мои проекты — UI Tests

## 1. Page Display

### 1.1 The projects page shows the user's feed as a grid
```gherkin
Given a signed-in user with projects
When they open the projects page
Then each project is shown as a card with its type icon, title and date
```

### 1.2 A recent-projects section shows the newest four
```gherkin
Given a signed-in user with more than four projects
When they open the projects page
Then a recent-projects section shows the first four
And a separate section below shows the full feed
```

### 1.3 An untitled document is labelled by its first line
```gherkin
Given a signed-in user with a document that has no title
When they open the projects page
Then that card is labelled with the start of the document's text
And not with its document type
```

### 1.4 A failed generation shows a retry action
```gherkin
Given a signed-in user with a failed generation
When they open the projects page
Then that card shows it failed
And offers a retry action
```

### 1.5 A recovering generation shows no retry action
```gherkin
Given a signed-in user with a generation stuck past the stale threshold
When they open the projects page
Then that card shows it is recovering
And offers no retry action
```

### 1.6 Inert controls are shown as unavailable
```gherkin
Given a signed-in user on the projects page
When they look at the category tabs, the per-project actions menu and the business document types
Then each is shown as unavailable
And each is announced as unavailable
And none of them responds to a click or takes keyboard focus
```

---

### 1.7 A card's date is shown in the viewer's own day
```gherkin
Given a project created just before midnight in the viewer's time zone
And a browser in a time zone other than UTC
When the feed is rendered
Then the card shows the viewer's local calendar date, not the UTC one
```

---

## 2. View Toggle

### 2.1 Switching to list view re-renders the same feed
```gherkin
Given a signed-in user viewing their projects as a grid
When they switch to list view
Then the same projects are shown as rows
And no new data is fetched
```

### 2.2 Switching views keeps the active search and scroll position
```gherkin
Given a signed-in user who has searched and scrolled down
When they switch between grid and list view
Then the search stays active
And the scroll position is preserved
```

---

## 3. Search

### 3.1 Searching filters the feed and shows the result count
```gherkin
Given a signed-in user with projects
When they type a term that matches some of them
Then only matching projects are shown
And the number of results is visible
```

### 3.2 The recent-projects section is hidden while searching
```gherkin
Given a signed-in user on the projects page
When they type a search term
Then the recent-projects section is no longer shown
```

### 3.3 The latest search wins regardless of response order
```gherkin
Given a signed-in user typing a search term
When an earlier search responds after a later one
Then the results shown are those of the later search
```

### 3.4 Typing does not fire a request per keystroke
```gherkin
Given a signed-in user on the projects page
When they type a term quickly
Then fewer requests are sent than characters typed
```

---

### 3.5 A search term carrying markup is displayed inert
```gherkin
Given the user searches for a term containing a script payload
When the results and the no-matches message are shown
Then the term is displayed as text in the message and in the input
And nothing from the term executes
And the term survives a reload through the address bar unchanged and still inert
```

---

## 4. Sorting

### 4.1 Choosing a sort order re-orders the feed and resets to the first page
```gherkin
Given a signed-in user on a later page of their projects
When they choose a different sort order
Then the feed is shown in that order
And they are returned to the first page
```

### 4.2 Sorting keeps the active search
```gherkin
Given a signed-in user with an active search
When they change the sort order
Then the search term stays applied
And the results remain filtered
```

---

### 4.3 The latest sort wins regardless of response order
```gherkin
Given the user changes the sort order twice in quick succession
When the first order's response arrives after the second's
Then the feed shows the second order's result
And it still does after the late response arrives
```

---

## 5. Retry

### 5.1 Retrying a failed generation starts a new one
```gherkin
Given a signed-in user with a failed generation
When they retry it
Then a new generation is started
And the failed card is still shown
```

### 5.2 A double click starts only one generation
```gherkin
Given a signed-in user with a failed generation
When they click retry twice in quick succession
Then only one generation is started
```

### 5.3 A failed retry restores the card and reports the error
```gherkin
Given a signed-in user whose retry request is rejected
When the rejection arrives
Then an error is shown on that card
And the retry action is available again
And no pending project is left in the feed
```

---

### 5.4 A shed retry does not re-arm the button immediately
```gherkin
Given a retry refused as too many requests with a retry-after hint
When the card is restored
Then the retry button stays unavailable for the stated interval
And it is not clickable on the next paint
```

### 5.5 Retrying work that has since finished refreshes instead of dead-ending
```gherkin
Given a card rendered while its generation was still unfinished
When the generation finishes and the user then clicks retry
Then no new project appears
And the feed shows the work's current state
```

---

## 6. State Persistence

### 6.1 Search, sort and page survive opening a project and returning
```gherkin
Given a signed-in user who searched, sorted and paged forward
When they open a project and navigate back
Then the same search, sort order and page are still applied
```

### 6.2 Search, sort and page survive a reload
```gherkin
Given a signed-in user who searched, sorted and paged forward
When they reload the page
Then the same search, sort order and page are still applied
```

### 6.3 The chosen view survives a reload
```gherkin
Given a signed-in user who has switched to list view
When they reload the page
Then the list view is shown
```

### 6.4 A corrupted stored view falls back to the default
```gherkin
Given the stored view preference holds a value the app does not recognise
When the user opens the projects page
Then the default view is shown
And the feed is not empty
```

---

## 7. Empty and Error States

### 7.1 A search with no matches offers to clear the search
```gherkin
Given a signed-in user with projects
When they search for a term that matches nothing
Then a no-matches message is shown
And the offered action clears the search
```

### 7.2 A user with no projects is offered to create one
```gherkin
Given a signed-in user with no projects
When they open the projects page
Then a no-projects-yet message is shown
And the offered action creates a project
And it is not the no-matches message
```

### 7.3 A failed load offers a retry that keeps search and sort
```gherkin
Given a signed-in user whose projects fail to load
When the error is shown
Then a retry action is offered
And using it repeats the request with the same search and sort order
```

### 7.4 The feed shows a loading state while it fetches
```gherkin
Given a signed-in user opening the projects page
When the feed has not yet arrived
Then a loading placeholder is shown in place of the cards
```

---

### 7.5 A failed later page keeps the rows already shown
```gherkin
Given the user has loaded the first page and requests the next
When that request fails
Then the projects already rendered stay visible
And an error with a retry affordance is shown for the failed page only
And the whole-page error state is not shown
```

### 7.7 Repeated retries against a failing backend back off
```gherkin
Given the projects request keeps failing
When the user retries several times in a row
Then the interval between attempts grows
And the attempts stop at the cap
```

### 7.6 A row repeated across two pages is rendered once
```gherkin
Given the first page and the next page share an item of the same kind and id
When the next page is appended
Then that project is rendered exactly once

Given a document and a generation sharing an id across those pages
Then both are rendered
```

---

## 8. Navigation

### 8.1 Opening a project card opens it in the editor
```gherkin
Given a signed-in user on the projects page
When they click a document card
Then the editor opens with that document
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a signed-in user` | Session with a valid access token; app shell rendered |
| `the projects page` | `/projects` route |
| `they retry it` | Click «Повторить» → `POST /api/v1/generations/{id}/retry` |
| `no new data is fetched` | No outgoing request observed during the interaction |
| `the stale threshold` | `GENERATION_STALE_AFTER_MINUTES`, default 10 |
| `the same search, sort order and page are still applied` | Restored from the URL query string |
| `opens the projects page` | Navigates to `/projects` through the UI, never by typing a URL |
| `a card` / `a row` | `[data-testid='project-card']` / `[data-testid='project-row']` |
| `the feed region` | `[data-testid='projects-feed']` |
| `a no-matches message` / `a no-projects-yet message` | `[data-testid='projects-empty-search']` / `[data-testid='projects-empty-none']` |
| `announced as unavailable` | `aria-disabled` and not reachable by keyboard focus |
| `the stored view preference` | Per-device client storage key for the grid/list choice |
| `fewer requests than characters` | Requests counted at the network layer over the typing window |
