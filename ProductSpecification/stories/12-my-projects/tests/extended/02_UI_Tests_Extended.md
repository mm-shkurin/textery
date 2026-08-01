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

### 1.2 A very long title does not break the card
```gherkin
Given a document whose title is far longer than the card
When the user opens «Мои проекты»
Then the title is truncated within the card
```

### 1.3 Both source kinds are visually distinguishable
```gherkin
Given the user owns a document and a failed generation
When they open «Мои проекты»
Then the two cards are told apart without reading their text
```

---

## 2. Search and Sort

### 2.1 Clearing the search restores the full feed
```gherkin
Given the user has searched
When they clear the query
Then the full feed is shown again
```

### 2.2 The recent section under an active search
```gherkin
Given the user has searched
When results are shown
Then the recent section behaves as the story pins it
```

### 2.3 Sorting is reachable by keyboard
```gherkin
Given the user is on «Мои проекты»
When they reach the sort control by keyboard alone
Then they can change the order without a mouse
```

---

## 3. Repeat

### 3.1 The repeat action is absent on an unknown status
```gherkin
Given a project whose status the app does not recognise
When the user opens «Мои проекты»
Then its card offers no repeat action
```

### 3.2 A repeat shows progress until it resolves
```gherkin
Given the user repeats a failed generation
When the new generation is still running
Then its card shows that it is in progress
```

---

## 4. Restored State

### 4.1 The page number survives a return from the editor
```gherkin
Given the user is on a later page of their projects
When they open a project and navigate back
Then the same page is shown
```

### 4.2 A shared link reproduces the same filtered feed
```gherkin
Given a feed narrowed by search and sort
When the same address is opened afresh
Then the same query, order, and page are shown
```

---

## DSL Technical Reference

Inherits `02_UI_Tests.md`.
