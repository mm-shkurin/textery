> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — API Tests (Extended)

## 1. Boundary Values

### 1.1 Volume at the exact boundaries (1 and 10) is accepted

```gherkin
Given a generation request with volume_pages of 1
When the client submits the request
Then the request is accepted

Given a generation request with volume_pages of 10
When the client submits the request
Then the request is accepted
```

### 1.2 Requirements/extra_wishes at exactly the length limit are accepted

```gherkin
Given a generation request whose requirements text is exactly at the maximum
  allowed length
When the client submits the request
Then the request is accepted
```

## 2. Whitespace & Encoding

### 2.1 A topic consisting only of whitespace is rejected like an empty topic

```gherkin
Given a generation request whose topic is only whitespace
When the client submits the request
Then the response is a validation error
```

> `2.2` (Cyrillic round-trip) was promoted to `01_API_Tests.md` §2.2 — hazard-catalogue
> scan (2026-07-06) found it closes a Core Requirement guard, so it belongs critical-path.

## 3. Idempotency Edge Cases

### 3.1 Different idempotency keys for otherwise-identical requests create separate generations

```gherkin
Given two identical generation requests submitted with different idempotency keys
When both are submitted
Then two separate generations are created
```

## 4. Pagination Edge Cases

### 4.1 An empty generation list returns an empty page, not an error

```gherkin
Given no generations exist yet
When a client requests the generation list
Then the response is an empty list with no next cursor
```
