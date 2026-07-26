# Export document — Load Tests

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`). Export adds CPU-heavy
render work per request; the risk is rate and concurrent render pressure.

## 1. Export Throughput

### 1.1 The export endpoint sustains the configured request rate
```gherkin
Given the configured throughput baseline
And a pool of caller-owned documents
When export requests arrive at the target sustained rate
Then the endpoint sustains that rate over the window
And the error rate stays under the ceiling
```
Threshold: sustained export rate over a 60s window; error-rate ceiling per baseline. Catches a render step that does not scale with request rate.

## 2. Concurrent Render Pressure

### 2.1 Concurrent renders are bounded, not unbounded
```gherkin
Given the configured throughput baseline
When many exports render concurrently on one instance
Then concurrent renders are bounded by a worker pool or backpressure
And a single instance is not exhausted
```
Threshold: concurrent render count capped; no unbounded native-memory/CPU growth. Catches a missing render concurrency limit.
