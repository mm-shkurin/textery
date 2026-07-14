> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — Security Tests (Extended)

## 1. Sanitizer Robustness

### 1.1 Nested and obfuscated injection payloads are neutralized the same as simple ones

```gherkin
Given saved content containing nested/obfuscated script payloads (e.g. encoded event
  handlers, mixed-case tags)
When the content is served to a client
Then the payload is neutralized the same as a plain unobfuscated payload
```

## 2. Header Injection

### 2.1 A malformed idempotency key is rejected, not passed through

```gherkin
Given a create request whose idempotency key contains header-breaking control
  characters
When the client submits the request
Then the request is rejected
And no malformed value reaches downstream storage or logs
```
