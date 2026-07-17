# Manual input mode (non-AI document creation) — Load Tests

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`, Load Challenge
Profile). Unlike story #1, this story has no async/queue step — creation and save are
both plain synchronous request/response operations. The load risk is therefore pure
request-rate capacity on two simple endpoints, not queue depth or worker concurrency.

---

## 1. Save Throughput

### 1.1 Document creation and save sustain the configured throughput baseline

```gherkin
Given the configured throughput baseline of concurrent clients
When each client creates a manual document and repeatedly saves content within the
  load window
Then the endpoints sustain the configured request rate over the window
And the error rate stays within the configured ceiling
```

Threshold: sustained request rate per the project's configured throughput baseline over
the load window; error-rate ceiling per the same baseline. Catches: request-handling
capacity regressions on the create/save path (e.g., an accidental synchronous DB lock
or missing connection pooling under concurrency).

---

## 2. Concurrency Conflicts Under Load

### 2.1 Version-conflict saves stay within a bounded rate and do not degrade overall throughput

```gherkin
Given the configured throughput baseline of concurrent clients, with a subset
  deliberately racing saves against the same small set of documents
When the load window runs
Then version-conflict (409) responses occur only for the deliberately racing saves
And the overall sustained request rate for non-conflicting saves is unaffected
```

Threshold: 409 rate matches the deliberately-induced conflict rate, not an unbounded
tail; non-conflicting request latency/throughput stays within the same baseline as
scenario 1.1. Catches: an optimistic-concurrency implementation that serializes/locks
more broadly than the single racing document, silently throttling unrelated saves.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `the configured throughput baseline of concurrent clients` | N concurrent clients per the project's load baseline, issuing `POST /api/v1/documents` then repeated `PUT /api/v1/documents/{document_id}` |
| `the endpoints sustain the configured request rate` | requests/sec measured over the load window against the configured target, across both endpoints |
| `the error rate stays within the configured ceiling` | non-2xx rate (excluding the deliberately induced 409s in scenario 2.1) measured over the load window |
| `deliberately racing saves against the same small set of documents` | a fixed subset of clients repeatedly `PUT` the same `document_id` concurrently with stale `version` values |
| `version-conflict (409) responses` | count of `409` responses attributable to the racing subset |
| `the overall sustained request rate for non-conflicting saves is unaffected` | throughput/latency for the non-racing majority of clients compared against scenario 1.1's baseline |
