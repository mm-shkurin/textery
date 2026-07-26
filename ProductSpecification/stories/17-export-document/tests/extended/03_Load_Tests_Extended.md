> These are additional edge case tests. Implement after core tests pass.

# Export document — Load Tests (Extended)

## 1. Mixed Format Load

### 1.1 Sustained mixed PDF and DOCX exports hold the rate
```gherkin
Given the configured throughput baseline
When exports arrive at the target rate split across pdf and docx
Then the endpoint sustains the rate over the window
And the error rate stays under the ceiling
```
Threshold: sustained mixed-format rate over the window. Catches a format-specific render bottleneck.
