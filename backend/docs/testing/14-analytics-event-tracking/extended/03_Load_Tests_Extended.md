<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — Load Tests (Extended)

Same **Throughput** profile as the critical file. These two exercise growth and fan-out
rather than steady rate, which is why they sit here: each catches a real regression, but
neither is on the path that must be green before the story ships.

---

## 1. Growth of the Abuse Counters

### 1.1 Counter rows stay bounded as distinct visitors accumulate
```gherkin
Given the configured throughput baseline
And events arriving from many distinct addresses across several elapsed windows
When the windows have elapsed
Then the number of stored counter rows is bounded by the live windows, not by the number of addresses seen
```

`Threshold: stored counter rows must not grow with cumulative distinct addresses.` Catches the
pruning step going missing — the table's own documentation says elapsed-window rows can be
dropped, and until this story nothing dropped them because nothing filled them.

---

## 2. Sweep Fan-Out

### 2.1 Recovering stalled generations does not multiply recorded events by instance count
```gherkin
Given the configured throughput baseline
And a backlog of stalled generations
And several instances running the recovery sweep on the same tick
When the sweep completes
Then the number of recorded events matches the number of generations
And the recovery completes within its window
```

`Threshold: recorded events == stalled generations, independent of instance count; sweep
duration < its interval.` Catches both the M×K emission fan-out and a sweep that outlasts its
own tick once each recovered row costs an extra write.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `many distinct addresses` | Distinct `client_source()` values driving distinct bucket keys |
| `several elapsed windows` | Advance the clock past the fixed window repeatedly |
| `several instances running the recovery sweep` | Multiple `run_stale_generation_sweep` loops against one database |
| `within its window` | Wall-clock duration under `SWEEP_INTERVAL_SECONDS` |
