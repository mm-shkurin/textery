> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — API Tests (Extended)

## 1. Boundary & Edge

### 1.1 Content exactly at the limit is accepted
```gherkin
Given a generation whose converted content is exactly at the code-point limit
When it is converted
Then the document is created
```

### 1.2 A grapheme straddling the limit is not split
```gherkin
Given a generation whose content places a multi-code-point grapheme across the limit boundary
When conversion is requested
Then it is refused on the pinned unit
And no partial grapheme is stored
```

### 1.3 An idempotency key outside the allowed length is refused
```gherkin
Given a completed generation
When conversion is requested with an idempotency key longer than allowed
Then the request is refused
```

## 2. Link Semantics

### 2.1 A converted document reports its generation link on read
```gherkin
Given a document created from a generation
When it is read
Then it reports the linked generation id
```

### 2.2 A manual document reports no generation link on read
```gherkin
Given a blank document created from scratch
When it is read
Then it reports no generation link
```
