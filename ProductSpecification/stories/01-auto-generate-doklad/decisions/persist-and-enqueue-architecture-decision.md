# Decision: Persist-and-Enqueue Architecture for Generation Creation

**Date**: 2026-07-09 **Scenarios**: 2.1 (and depended on by 2.2, 3.1, 3.2, 4.1-4.3, 5.1-5.6, Infra 5.1-5.3)

First scenario requiring real persistence and a job queue — needed one architecture for
how a valid request becomes a durable, queryable row and an async job before any later
scenario (idempotency, status polling, retry, reconciliation) can build on it.

| Rejected | Why |
|----------|-----|
| Transactional outbox (single-transaction persist+publish) in 2.1 | Solves the persist-then-enqueue ordering gap immediately, but is materially more work than this scenario's happy-path scope needs; the gap it closes is already covered by planned Infra Scenario 5.2 (reconciliation sweep for a job silently never enqueued). Deferred, not dropped. |
| `status` as a native Postgres ENUM type | Additive-only (can't rename/remove values without a full table rewrite); a CHECK constraint gives the same illegal-value rejection and is cheaper to evolve when section 5 adds `in_progress`/`completed`/`failed` transitions. |

**Chosen**: `Generation.create(...)` domain factory also generates `id` (uuid4),
`status` ("pending"), `created_at` (UTC now) — pure domain, no I/O. `RequestGeneration`
usecase: `Generation.create(...)` → `GenerationStorage.save()` (commits before
returning) → `GenerationQueue.enqueue()` → return. New ports `GenerationStorage`
(SQLAlchemy/Postgres adapter, first `generations` migration) and `GenerationQueue`
(arq/Redis adapter).

## Model

- `Generation` domain entity gains `id: UUID`, `status: str`, `created_at: datetime`
  fields (previously validation-only, ended in `NotImplementedError`).
- New usecase-layer port `GenerationStorage.save(generation) -> None`.
- New usecase-layer port `GenerationQueue.enqueue(generation_id) -> None`.
- `generations` table: `status` column is `VARCHAR` + CHECK constraint restricting to
  `{pending, in_progress, completed, failed}` — not a native enum.
- Storage adapter must commit (not just flush) before `save()` returns, and must
  release its session/connection on any exception raised after `save()` (including a
  downstream `queue.enqueue()` failure) — no leaked connections on the error path.

## Edge Cases

| Case | Behavior |
|------|----------|
| `queue.enqueue()` fails/times out after `storage.save()` already committed | Generation row stays durably "pending" with no job ever enqueued. NOT resolved in 2.1 — covered by Infra Scenario 5.2 (reconciliation sweep for a silently-never-enqueued job). |
| Client GETs the generation immediately after the 201 | Not testable until the GET endpoint exists — covered by Backend Scenario 4.1 ("pending generation reports its status" immediately after creation), which is the real read-after-write guard. |
| Illegal `status` value written by a future bug or manual UPDATE | Rejected at the DB layer by the CHECK constraint, independent of application validation. |
