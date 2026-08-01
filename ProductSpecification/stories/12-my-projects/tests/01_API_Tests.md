> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the merged read and its ownership predicate, then search, then sort and
> paging, then the repeat command and its exactly-once rule.

# Мои проекты — API Tests

Black-box over `GET /api/v1/projects` and `POST /api/v1/generations/{id}/repeat`.
Contracts: `api-specs/projects_list.yaml`, `api-specs/projects_schemas.yaml`,
`api-specs/generations_repeat.yaml`.

---

## 1. Ownership Guards

### 1.1 The feed contains only the caller's work
```gherkin
Given two accounts each own documents and generations
When one of them requests their projects
Then only that account's items are returned
```

### 1.2 A repeat of another account's generation is indistinguishable from a missing one
```gherkin
Given a generation owned by another account
And a generation id that exists nowhere
When the caller requests a repeat of each in turn
Then both answers are identical in status and body
And no generation is created
```

---

## 2. Feed Membership

### 2.1 Documents and unconverted generations arrive as one feed
```gherkin
Given the caller owns a document and a generation that never became a document
When they request their projects
Then both appear as items
And each carries its own kind
```

### 2.2 A converted generation appears once, as its document
```gherkin
Given a generation that has been converted into a document
When the caller requests their projects
Then the work appears exactly once
And it appears as the document, not as the generation
```

### 2.3 A conversion committing during the read is still counted once
```gherkin
Given a generation being converted into a document
When the projects feed is read while that conversion commits
Then the work appears exactly once in the returned page
```

### 2.4 A generation converted before the document link existed does not appear twice
```gherkin
Given a legacy generation whose document link was never back-filled
When the caller requests their projects
Then the work appears exactly once
```

### 2.5 A completed generation whose conversion failed is a repeatable feed item
```gherkin
Given a generation that completed but whose conversion to a document failed
When the caller requests their projects
Then the item is present with a defined status
And the item is offered as repeatable
```

### 2.6 One arm failing fails the whole request
```gherkin
Given the generation source cannot be read
When the caller requests their projects
Then the request fails
And no partially populated page is returned
```

---

## 3. Search

### 3.1 Search matches title, generation topic, and document text
```gherkin
Given items whose match lives in the title, the topic, and the body respectively
When the caller searches for a term present in each
Then all three items are returned
```

### 3.2 Search ignores case and normalization form
```gherkin
Given a document whose title is stored in decomposed form
When the caller searches for the composed form of that title
Then the document is returned
And the same holds with the two forms exchanged
```

### 3.3 Wildcards in the query are literal text
```gherkin
Given the caller owns several documents
When they search for a query consisting only of a wildcard character
Then only documents containing that character literally are returned
```

### 3.4 A query matching nothing is an empty page, not an error
```gherkin
Given the caller owns documents
When they search for a term present in none of them
Then the request succeeds with no items
And the reported total is zero
```

### 3.5 An over-long query is rejected
```gherkin
Given a search query longer than the configured maximum
When the caller requests their projects
Then the request is rejected as invalid
And no search is executed
```

---

## 4. Sorting and Paging

### 4.1 Each sort order returns the documented sequence
```gherkin
Given a mixed feed of documents and generations
When the caller requests each of the five sort orders in turn
Then each returns the items in the order that order defines
```

### 4.2 Ordering is total when the sort key ties
```gherkin
Given a document and a generation sharing an id value and a creation instant
When the caller pages through the feed twice
Then both reads return the same order
```

### 4.3 Titles order under the pinned collation with untitled items last
```gherkin
Given documents titled in Cyrillic, in Latin, in mixed case, and untitled
When the caller sorts by title
Then the titled items follow the pinned collation's order
And the untitled items come last
```

### 4.4 Sorting survives an active search
```gherkin
Given a search that matches several items
When the caller changes the sort order without changing the query
Then the results are the same set in the new order
And the response is the first page
```

### 4.5 An unknown sort order is rejected rather than silently replaced
```gherkin
Given a sort order that does not exist
When the caller requests their projects
Then the request is rejected as invalid
And no feed is returned
```

### 4.6 Page and limit bounds are enforced, not clamped
```gherkin
Given the caller requests a limit above the maximum
And separately a page above the ceiling
And separately a page below one
Then each request is rejected as invalid
```

### 4.7 A page past the end of the results is empty, not an error
```gherkin
Given the caller owns fewer items than one page holds
When they request the second page
Then the request succeeds with no items
And the reported total still counts every matching item
```

### 4.8 An insert during paging skips at most one item
```gherkin
Given the caller reads the first page of their projects
When an item that sorts into that page is created before they read the second
Then the second page omits at most one item
And no item is returned twice
```

---

## 5. Projection

### 5.1 An untitled document carries a plain-text preview instead of a title
```gherkin
Given an untitled document whose stored content is marked-up text
When the caller requests their projects
Then the item carries a preview containing no markup
And no full document content is returned
```

### 5.2 A preview cut inside a multi-code-point character stays whole
```gherkin
Given an untitled document whose text places a composed emoji and a combining accent
      at the preview limit
When the caller requests their projects
Then the preview ends on a whole character
```

---

## 6. Repeat — State Rules

### 6.1 A failed generation can be repeated
```gherkin
Given a failed generation owned by the caller
When they request a repeat
Then a new generation is created with the source's parameters
And the source generation is unchanged
```

### 6.2 A stalled generation becomes repeatable once it goes stale
```gherkin
Given a generation left in progress
When the staleness deadline has not yet passed and a repeat is requested
Then the request is refused as not repeatable
And when the deadline has passed and a repeat is requested
Then a new generation is created
```

### 6.3 A generation that became a document cannot be repeated
```gherkin
Given a generation that has since completed and become a document
When the caller requests a repeat from a card rendered before that happened
Then the request is refused as not repeatable
And the refusal carries the source's current status
```

---

## 7. Repeat — Exactly Once

### 7.1 A double-click produces one generation
```gherkin
Given a failed generation owned by the caller
When two repeats of it are requested one after the other
Then only one generation is created
And both answers name the same generation
```

### 7.2 Two concurrent repeats produce one generation
```gherkin
Given a failed generation owned by the caller
When two repeats of it are released simultaneously against separate instances
Then only one generation is created
And neither caller receives an error
```

### 7.3 A repeat can itself be repeated after it fails
```gherkin
Given a failed generation whose repeat has also failed
When the caller requests another repeat
Then a second new generation is created
```

### 7.4 A source whose repeat already succeeded can be repeated again
```gherkin
Given a failed generation whose repeat completed and became a document
When the caller requests another repeat of the source
Then a new generation is created
And the completed repeat is not returned in its place
```

### 7.5 A repeat cannot be aimed at another account's parameters
```gherkin
Given a repeat request carrying an owner, a status, and a document link in its body
When the caller requests the repeat
Then the created generation belongs to the caller
And its status is the initial one
```

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|--------------------------|
| `the caller` / `an account` | Bearer JWT; `owner_id` taken from the token |
| `requests their projects` | `GET /api/v1/projects` |
| `searches for X` | `GET /api/v1/projects?q=X` |
| `sorts by X` | `GET /api/v1/projects?sort=X` |
| `requests a repeat` | `POST /api/v1/generations/{id}/repeat` |
| `rejected as invalid` | 422 with the contract's error code |
| `refused as not repeatable` | 409 `NOT_REPEATABLE` |
| `indistinguishable` | Byte-identical status and body |
| `released simultaneously` | Two requests held at a latch, then released |
| `the staleness deadline` | `generation_stale_after` config key |
| `the pinned collation` | `projects_sort_collation` (`ru-RU-x-icu`) |
