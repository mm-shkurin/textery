# Expected Load

- Multi-tenant SaaS — many independent users, not single-user.
- Target: hundreds of concurrent users (not just a small demo stand) — confirmed with
  the user 2026-07-06.
- Consequence for architecture: text generation must be async/queued (background task +
  polling or websocket/status endpoint), not a synchronous request held open for the
  duration of an LLM call. DB access needs connection pooling sized for that concurrency.
- Data volume: not yet bounded — revisit once generation/history story specs land.
