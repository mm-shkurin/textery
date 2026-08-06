> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — UI Tests (Extended)

## 1. The chosen view survives a reload

```gherkin
Given the user switched to list view
When the user reloads the page
Then the feed is still rendered as a list
```

## 2. Clearing the search restores the recent-projects section

```gherkin
Given an active search
When the user clears the query
Then the full feed is shown again
And the recent-projects section reappears
```

## 3. A long project title is truncated without breaking the card layout

```gherkin
Given a project whose title is far longer than the card
When the feed is rendered
Then the title is truncated within the card bounds
```

## 4. The result count updates as the query narrows

```gherkin
Given an active search returning several results
When the user extends the query so fewer match
Then the displayed result count matches the returned results
```

## 5. Pressing Enter in the search field does not submit a page reload

```gherkin
Given focus in the search field
When the user presses Enter
Then the feed updates in place without a full page reload
```

## 6. Inert controls do not navigate

```gherkin
Given the category filters and the actions menu are shown as unavailable
When the user clicks them
Then nothing is navigated and no request is sent
```

## 7. The retry button is disabled while its request is in flight

```gherkin
Given the user clicked retry on a failed generation
When the request has not yet returned
Then the button is disabled
```

## 8. An empty search result keeps the sort selection visible

```gherkin
Given a non-default sort and a query matching nothing
When the empty state is shown
Then the chosen sort is still displayed
```
