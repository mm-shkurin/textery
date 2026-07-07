> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — Integration Tests (Extended)

## 1. Partial Provider Responses

### 1.1 A provider response that succeeds but returns suspiciously short content is still accepted

```gherkin
Given the generation provider returns a very short but well-formed result
When the background worker processes it
Then the generation still completes successfully with that content
And no arbitrary minimum-length rule blocks a legitimately short response
```

> `2.1` (retry jitter under concurrent shared outage) was promoted to
> `06_Integration_Tests.md` §8.1 — hazard-catalogue scan (2026-07-06) found it closes a
> named Core Requirement (randomized jitter) and a real thundering-herd risk against a
> paid external API, so it belongs critical-path.
