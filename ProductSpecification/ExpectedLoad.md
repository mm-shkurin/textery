# Expected Load

- Multi-tenant SaaS — many independent users, not single-user.
- Target: hundreds of concurrent users (not just a small demo stand) — confirmed with
  the user 2026-07-06.
- Consequence for architecture: text generation must be async/queued (background task +
  polling or websocket/status endpoint), not a synchronous request held open for the
  duration of an LLM call. DB access needs connection pooling sized for that concurrency.
- Data volume: not yet bounded — revisit once generation/history story specs land.

## Load Challenge Profile

**Throughput.** The dominant production risk is request *rate*, not per-user data
volume, response-time SLOs, or batch/ETL processing: hundreds of concurrent users each
submitting generation requests, with capacity-per-second (API request handling, queue
depth, worker concurrency, downstream GigaChat rate limits) as the binding constraint.
Queue depth/worker concurrency currently mean the in-process `BackgroundTasks` queue, not
`arq` — see `.memory-bank/tasks/known-debt.md` #13; revisit this profile's queue-specific
assertions once `arq` actually lands. Load scenarios for any story should assert sustained request rate, queue
depth bounds, and downstream rate-limit compliance — not full-table volume scale or
p95/p99 latency SLOs (this product has no interactive-trading-style latency
requirement) or batch-job duration (no ETL/batch pipeline exists).
