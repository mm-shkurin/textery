# Auto-generate: доклад — Load Tests

Profile: **Throughput** (see `ProductSpecification/ExpectedLoad.md`, Load Challenge
Profile). Story 1 is the endpoint this profile is written for — hundreds of concurrent
users submitting generation requests, with request rate, `arq` queue depth, and worker
concurrency as the binding constraint (not per-user data volume or a latency SLO).

---

## 1. Submission Throughput

### 1.1 Generation submission sustains the configured throughput baseline

```gherkin
Given the configured throughput baseline of concurrent clients
When each client submits a generation request within the load window
Then the endpoint sustains the configured request rate over the window
And the error rate stays within the configured ceiling
```

Threshold: sustained request rate per the project's configured throughput baseline over
the load window; error-rate ceiling per the same baseline. Catches: request-handling
capacity regressions (e.g., an accidentally-synchronous code path reintroducing the LLM
call into the request/response cycle).

---

## 2. Queue Depth Under Burst

### 2.1 A burst of submissions does not exceed the worker concurrency ceiling

```gherkin
Given a burst of generation requests larger than the configured worker concurrency ceiling
When the burst is submitted
Then no more than the configured number of jobs run concurrently
And the remaining jobs queue instead of overwhelming the generation provider
```

Threshold: concurrently-executing jobs never exceed the configured `arq` `max_jobs`
ceiling (see story spec's Core Requirements). Catches: a missing or misconfigured
concurrency cap that would let a burst drive unbounded parallel calls to the external
generation provider.

---

## 3. Recovery After a Load Spike

### 3.1 Throughput recovers after a burst subsides

```gherkin
Given the endpoint has just handled a burst above the configured throughput baseline
When the burst subsides back to the baseline rate
Then the endpoint returns to the baseline error rate within the recovery window
```

Threshold: error rate returns to baseline within the project's configured recovery
window after a burst. Catches: connection-pool or queue-backlog exhaustion that doesn't
self-heal after a spike — promoted from an edge case to critical-path because this
story's declared Load Challenge Profile is Throughput, making burst-recovery a
first-class concern rather than a nice-to-have.

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---|---|
| `the configured throughput baseline of concurrent clients` | N concurrent `POST /api/v1/generations` clients per the project's load baseline |
| `the endpoint sustains the configured request rate` | requests/sec measured over the load window against the configured target |
| `the error rate stays within the configured ceiling` | non-2xx rate measured over the load window |
| `the configured worker concurrency ceiling` | `arq` `max_jobs` setting (see `templates/scheduling/implementation.md`) |
| `no more than the configured number of jobs run concurrently` | concurrent in-flight job count measured against `max_jobs` during the burst |
| `the endpoint has just handled a burst` | load generator ramps request rate above the configured baseline, then back down |
| `returns to the baseline error rate within the recovery window` | error-rate metric sampled after the burst ends, compared to the pre-burst baseline |
