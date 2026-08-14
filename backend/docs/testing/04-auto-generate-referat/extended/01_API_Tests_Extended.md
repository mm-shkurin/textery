<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — API Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

---

## 1. Prompt Text Handling

### 1.1 The template survives storage and transport byte-exact

```gherkin
Given a реферат request whose topic contains combining accents and emoji
When the prompt is built and sent
Then the provider receives the text byte-exact after normalization
```

The template is Cyrillic literal text in source, and the topic is arbitrary user text.
Both cross a file encoding, an HTTP body, and a JSON serializer before reaching GigaChat.

### 1.2 A maximum-length request stays within the prompt bound

```gherkin
Given a реферат request with topic, requirements and extra wishes each at their maximum
When the prompt is built
Then its length stays within the documented bound
```

The field caps are story 1's; what is new is the fixed template overhead added on top.
The bound is the sum, and nothing asserts it unless this does.

### 1.3 An empty optional field does not leave a dangling label in the prompt

```gherkin
Given a реферат request with no requirements and no extra wishes
When the prompt is built
Then the prompt names neither field
And the реферат structural instructions are still present
```

Absent-vs-empty: a template that always interpolates both fields emits "Требования: " with
nothing after it, which reads to the model as an instruction with a blank answer.

---

## 2. Type Boundary

### 2.1 A type differing only by case or whitespace is rejected

```gherkin
Given an authenticated user
When the user submits a generation request for "Реферат" or "реферат " 
Then the request is rejected as an unsupported document type
```

The domain allowlist matches exactly after NFC normalization — deliberately
case-sensitive, since the client picks from an enum rather than typing free text.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `byte-exact after normalization` | NFC-normalized comparison at the stub |
| `the documented bound` | Field caps (300 + 2000 + 2000) plus the pinned template constant |
| `rejected as an unsupported document type` | 422 `INVALID_DOCUMENT_TYPE` |
