> These are additional edge case tests. Implement after core tests pass.

# AI chat editing — Load Tests (Extended)

### 1.1 Reconnect replay under load does not amplify database work
```gherkin
Given the configured throughput baseline
When a share of the open streams reconnect and replay their tails at the same time
Then the per-stream query rate stays within its bound
And the reconnects are not synchronised on one tick
```

Threshold: tail-query rate per stream at the configured polling interval. Catches a
reconnect storm turning into a query storm.

### 1.2 A worker restart under load loses no accepted edit
```gherkin
Given the configured throughput baseline
When the worker is restarted mid-window
Then every accepted edit eventually reaches a terminal state
And the submission error rate stays under the ceiling
```

Threshold: zero accepted-but-never-terminal edits after the reclaim window.
