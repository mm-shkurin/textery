> These are additional edge case tests. Implement after core tests pass.

# Manual input mode (non-AI document creation) — Load Tests (Extended)

## 1. Recovery After a Load Spike

### 1.1 Throughput recovers after a burst subsides

```gherkin
Given the create/save endpoints have just handled a burst above the configured
  throughput baseline
When the burst subsides back to the baseline rate
Then the endpoints return to the baseline error rate within the recovery window
```
