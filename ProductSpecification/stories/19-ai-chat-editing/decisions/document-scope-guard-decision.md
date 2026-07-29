# Decision: Document-scope guard for the seven AI-edit endpoints

**Date**: 2026-07-29 **Scenarios**: 1.1 (binding on 1.2, 1.3, 2.x, 4.x, 6.x, 7.x)

A foreign document and an absent one must be refused identically on all seven endpoints,
and a resolver that merely runs *first* does not survive the ordering, concurrency and
disclosure hazards the catalogue scan found behind that requirement.

| Rejected | Why |
|----------|-----|
| Structural scoping only (port predicates, no resolver) | Leaves check-ordering to seven independent authors; the one that validates before resolving leaks existence through 409 or 422 without ever returning a wrong status |
| Shared resolver returning the full `Document` | Materialises up to a 200 000-unit `content` field on every request to all seven endpoints to answer a yes/no question |
| REST-layer `Depends()` guard | Puts an authorization policy in the adapter; the controller would decide a rule instead of delegating to a usecase |

**Chosen**: `resolve_owned_document` — a shared usecase-layer helper that is deliberately
**not** a usecase (usecases must not call usecases) — called as the first statement of all
seven usecases, over ports that carry ownership as a query predicate on reads *and* writes.

## Model

- `resolve_owned_document(document_repository, document_id, owner_id) -> DocumentScope`,
  raising `NotFoundException` when the repository returns `None`.
- `DocumentScope` — a bounded projection (`id`, `owner_id`, `version`). Deliberately not
  `Document`: nothing on the guard path needs `content`.
- Extends story 5's rule (`05-manual-mode/decisions/document-ownership-decision.md`): no
  story-19 port method may take a bare `document_id`. Every read **and every write**
  carries `(document_id, owner_id)` as predicates, so a write is conditional in its own
  right rather than trusting the resolver's earlier read — the resolve-then-write window
  is otherwise check-then-act on a multi-instance backend.
- Edit and revision lookups additionally carry `document_id`: the path document id is
  authoritative, so a caller's own edit under another of their documents is not found.
- One canonical refusal body for all seven, emitted by the existing
  `not_found_exception_handler`. The exception raised by `resolve_owned_document` carries
  **no** foreign document id — that handler logs the exception verbatim at INFO.

## Edge Cases

| Case | Behavior |
|------|----------|
| Foreign document, `base_version` that would have been correct | 404, byte-identical to the stale-version case. Never 409 — the status must not disclose that the version was right |
| Foreign document, malformed or over-long instruction | 404, byte-identical. Never 422/400 — resolution precedes validation |
| Foreign document on `.../stream` | Plain non-streaming JSON 404. Never a 200 `text/event-stream` carrying an error frame |
| Foreign but **real** `edit_id` on `/cancel`, or real `revision_number` on `/restore` | 404, and the seeded record is byte-identical afterwards. "Creates no rows" does not cover a mutation |
| Refused `POST /ai-edits` | Zero quota charge and zero enqueued jobs. Asserted on the queue directly, not on the chat message a worker would later write from it |
| Document repository errors or times out | Denied, never a permissive fallthrough. No row written |
| Refusal logging | Neither the foreign document id nor the instruction text reaches any sink |
