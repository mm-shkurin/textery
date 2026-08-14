<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/03_Load_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Editor pages — Load Tests

Profile: **Throughput** (`ProductSpecification/ExpectedLoad.md`) — the binding constraint is
request rate, not per-user data volume. Pagination itself is measured in the browser and
costs the server nothing, so the only surface this story puts under rate pressure is
**export**, which each document now makes strictly more expensive: full geometry, headers,
footers and page numbering on every render, synchronously, holding a request thread.

---

## 1. Export Under Rate

### 1.1 Export sustains its rate with page settings applied
```gherkin
Given the configured throughput baseline
And documents carrying non-default page settings with headers and page numbering
When export requests are issued at the target rate over the measurement window
Then the endpoint sustains the target rate
And the error rate stays under the ceiling
And no request exceeds the render deadline
```

Threshold: the project's configured sustained rate over the standard window; error-rate
ceiling as declared in the load baseline. Catches the regression where applying geometry
per render pushes per-request cost past what the instance can absorb at rate.

### 1.2 Concurrent renders stay bounded under sustained export load
```gherkin
Given the configured throughput baseline
And export requests arriving faster than renders complete
When the load is sustained over the measurement window
Then the number of renders in flight stays within the configured bound
And excess requests are shed or queued according to the configured policy
And render resources return to baseline after the load stops
```

Threshold: the render-concurrency bound already established by story 17. Catches both a
regression of that bound and a resource leak on the new geometry/header path — including
its failure branch, which this story adds.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's declared sustained-rate baseline from `ExpectedLoad.md` |
| `the render deadline` | The existing per-render wall-clock timeout (story 17 config) |
| `the configured bound` | Story 17's concurrent-render limit / worker pool size |
| `render resources` | In-flight render count and process memory, sampled before and after |
