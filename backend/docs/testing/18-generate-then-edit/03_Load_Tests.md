<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Generate → edit — Load Tests

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`). This story adds the
conversion endpoint on top of the generation request rate, and re-invokes story-1's poll
loop. The binding risk is request rate, not per-user data volume.

---

## 1. Conversion Endpoint Throughput

### 1.1 The conversion endpoint sustains the configured request rate
```gherkin
Given the configured throughput baseline
And a pool of completed generations owned by callers
When conversion requests arrive at the target sustained rate
Then the endpoint sustains that rate over the window
And the error rate stays under the ceiling
```
Threshold: sustained conversion rate over a 60s window; error-rate ceiling per the baseline. Catches a parse/sanitize step that does not scale with request rate.

---

## 2. Poll Load

### 2.1 Completion polls are spread, not lockstep
```gherkin
Given many generations completing around the same time
When their clients poll for completion
Then the polls are jittered across the interval
And do not arrive as a single synchronized burst
```
Threshold: poll arrivals spread across the interval, no synchronized spike. Catches a thundering-herd regression on the generation status endpoint. Reconcile with story-1's poll ownership.
