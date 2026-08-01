> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — API Tests (Extended)

## 1. A search query of exactly the length bound is accepted

```gherkin
Given a search query of exactly 200 code points
When the caller lists projects
Then the request succeeds
```

## 2. Combining diacritics in the query match their precomposed stored form

```gherkin
Given a document whose title is stored in precomposed form
When the caller searches with the same text in decomposed form
Then the document is matched
```

## 3. A limit of 1 pages the whole feed one item at a time

```gherkin
Given a feed of several projects
When the caller pages through it with a limit of 1
Then every item is returned exactly once, in the requested sort order
```

## 4. Leading and trailing whitespace in the query is trimmed before matching

```gherkin
Given a document whose title contains a distinctive word
When the caller searches for that word surrounded by spaces
Then the document is matched
```

## 5. A query consisting only of escaped metacharacters matches literally

```gherkin
Given a document whose title contains a percent sign
When the caller searches for a percent sign
Then only documents containing that character are returned
```

## 6. Sorting by type groups documents and generations of the same type together

```gherkin
Given documents and generations of several document types
When the caller sorts by type
Then items of one type are contiguous regardless of kind
```

## 7. A retry issued after the source has been retried to its cap is refused before any write

```gherkin
Given a source generation at its retry cap
When the caller retries it with a fresh idempotency key
Then the request is refused
And no generation row is created
```

## 8. The preview of a document shorter than the preview bound is returned whole

```gherkin
Given a document whose content is shorter than the preview bound
When the caller lists projects
Then the preview equals the full content
```

## 9. A page request with a limit of 100 returns at most 100 items

```gherkin
Given a feed larger than 100 items
When the caller requests a limit of 100
Then exactly 100 items are returned
```

## 10. Repeating an identical list request returns an identical page

```gherkin
Given a feed that is not being written
When the caller repeats the same list request
Then the two responses are identical, including total
```
