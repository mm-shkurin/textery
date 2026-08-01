> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the feed rendering in both views, then search and sort, then the non-happy
> states, then «Повторить», then navigation and restored state.

# Мои проекты — UI Tests

Selenium against the real stack. Reuses `frontend/src/features/history/`; the grid
layout, the view toggle, and the search/sort controls are new.

---

## 1. Feed Display

### 1.1 The feed renders the user's work as cards
```gherkin
Given the user owns several projects
When they open «Мои проекты»
Then each project is shown as a card with its type, its name, and its date
```

### 1.2 An untitled document shows its first line instead of a type label
```gherkin
Given the user owns a document that has never been titled
When they open «Мои проекты»
Then that card shows the beginning of the document's text
```

### 1.3 The list view shows the same work as rows
```gherkin
Given the user is looking at the grid view
When they switch to the list view
Then the same projects are shown as rows
```

### 1.4 «Недавние проекты» shows the newest work above the full list
```gherkin
Given the user owns more projects than the recent section holds
When they open «Мои проекты»
Then the recent section shows the newest of them
And the full list below shows the page
```

### 1.5 Out-of-scope controls are inert
```gherkin
Given the user is looking at the feed
When they reach the category tabs, the per-project menu, and a business document type
Then none of them can be clicked or focused
And each is announced as unavailable
```

---

## 2. Search

### 2.1 Searching narrows the feed
```gherkin
Given the user owns projects with different titles
When they type a term matching one of them
Then only the matching project remains
```

### 2.2 A search matching nothing offers to clear the search
```gherkin
Given the user has searched for a term matching none of their work
When the results arrive
Then an empty state is shown offering to reset the search
```

### 2.3 A user with no work at all is offered to create a project
```gherkin
Given the user owns no projects
When they open «Мои проекты»
Then an empty state is shown offering to create a project
And it is not the empty state shown for an unmatched search
```

### 2.4 Typing does not fire one request per keystroke
```gherkin
Given the user is on «Мои проекты»
When they type a multi-character term without pausing
Then fewer requests are sent than characters typed
```

### 2.5 A slow earlier search never overwrites a newer one
```gherkin
Given the user's first search is slower to answer than their second
When both answers arrive out of order
Then the feed shows the results of the term currently in the box
```

---

## 3. Sorting and Paging

### 3.1 Changing the sort reorders the feed
```gherkin
Given the user is looking at the feed
When they pick a different sort order
Then the same projects are shown in the new order
```

### 3.2 Changing the sort keeps the search and returns to the first page
```gherkin
Given the user has searched and moved to a later page
When they change the sort order
Then the query is still in the box
And the first page of the new order is shown
```

---

## 4. Non-Happy States

### 4.1 The feed shows a skeleton while it loads
```gherkin
Given the projects request has not answered yet
When the user opens «Мои проекты»
Then a loading placeholder is shown in the feed region
And no empty state is shown
```

### 4.2 A failed load offers a retry without blanking the page
```gherkin
Given the projects request fails
When the user opens «Мои проекты»
Then an error with a retry action is shown in the feed region
And the page's own chrome is still present
```

### 4.3 Repeated retries against a failing backend back off
```gherkin
Given the projects request keeps failing
When the user retries several times in a row
Then the interval between attempts grows
And the attempts stop at the cap
```

---

## 5. Repeat («Повторить»)

### 5.1 A failed generation is shown as a card with a repeat action
```gherkin
Given the user owns a generation that failed
When they open «Мои проекты»
Then its card shows the failure
And it offers to repeat the work
```

### 5.2 Repeating leaves the original card and adds one new one
```gherkin
Given the user is looking at a failed generation's card
When they repeat it
Then the original card is still shown
And exactly one new project appears
```

### 5.3 A double-click repeats once
```gherkin
Given the user is looking at a failed generation's card
When they click repeat twice in quick succession
Then exactly one new project appears
```

### 5.4 A failed repeat leaves no phantom card
```gherkin
Given a repeat whose request fails
When the user repeats a failed generation
Then no new card is shown
And an error offering another attempt is shown on the original card
And reloading the page shows the same thing
```

### 5.5 Repeating work that has since finished refreshes instead of dead-ending
```gherkin
Given a card rendered while its generation was still unfinished
When the generation finishes and the user then clicks repeat
Then no new project appears
And the feed shows the work's current state
```

---

## 6. Navigation and Restored State

### 6.1 Opening a project card opens it in the editor
```gherkin
Given the user is looking at their projects
When they click a document card
Then that document opens in the editor
```

### 6.2 Returning from the editor restores the search, sort, and view
```gherkin
Given the user has searched, sorted, and switched to the list view
When they open a project and then navigate back
Then the same query, order, and view are shown
```

### 6.3 The chosen view survives a reload
```gherkin
Given the user has switched to the list view
When they reload the page
Then the list view is shown
```

### 6.4 A corrupted stored view falls back to the default
```gherkin
Given the stored view preference holds a value the app does not recognise
When the user opens «Мои проекты»
Then the default view is shown
And the feed is not empty
```

### 6.5 The empty state's create action reaches the create flow
```gherkin
Given the user owns no projects
When they use the create action in the empty state
Then the create flow opens
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|--------------------------|
| `opens «Мои проекты»` | Navigates to the projects route through the UI, never by typing a URL |
| `a card` / `a row` | `[data-testid='project-card']` / `[data-testid='project-row']` |
| `the feed region` | `[data-testid='projects-feed']` |
| `an empty state` | `[data-testid='projects-empty-search']` / `[data-testid='projects-empty-none']` |
| `announced as unavailable` | `aria-disabled` and not reachable by keyboard focus |
| `repeat` | The card's «Повторить» control → `POST /api/v1/generations/{id}/repeat` |
| `the stored view preference` | Per-device client storage key for the grid/list choice |
| `fewer requests than characters` | Requests counted at the network layer over the typing window |
