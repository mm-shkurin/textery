# Task 7: Bound the stale-generation sweep query

Type: refactoring

## Why

`SqlAlchemyGenerationStorage.list_stale`
(`backend/adapters/db/src/access/generation/generation_storage.py:141`) selects **every**
pending/`in_progress` row older than the threshold, with no `LIMIT` and no ordering. The
usecase that consumes it, `RequeueStaleGenerations`
(`backend/usecase/src/generation/requeue_stale_generations.py`), then materializes the whole
result and requeues row by row. Every replica runs this sweep in its lifespan on the same
un-jittered tick.

After an outage the stale set is exactly at its largest — which is when a single activation
loads the entire backlog into one process's memory, when M replicas all load it, and when one
activation is most likely to outlast `SWEEP_INTERVAL_SECONDS`. The per-row CAS in storage
already makes contention correct, so this is a scale problem, not a correctness one.

The risk **predates Story 14** and was surfaced by that story's load-test spec.

## Why it is not Story 14's

Story 14 (Analytics Event Tracking) was written under the governing principle that analytics
adapts to the existing application and the existing application is not changed for analytics.
Adding a `LIMIT` changes how the recovery sweep behaves for **every** generation, analytics or
not. Story 14 also does not need it: the requeue path emits no analytics event by design, so a
recovered row costs Story 14 no extra write — the completion write it eventually costs is the
same one an ordinary generation costs.

Decided out of scope for Story 14 on 2026-08-19. The scenario is marked `[S]` at
`ProductSpecification/stories/14-analytics-event-tracking/tests/03_Load_Tests.md` §3.1, whose
Gherkin and threshold are the acceptance target for this task:

> `Threshold: rows fetched per activation <= the named batch size, independent of backlog
> depth.`

## Scope

- A named, configurable batch size for the sweep (a default in the same place the other sweep
  settings are named — do not inline a magic number).
- `list_stale` takes that limit and applies a deterministic order, so successive activations
  drain the backlog instead of re-reading the same head.
- The remaining backlog is drained across subsequent activations — one activation must not be
  the only chance a stalled row gets.
- Behaviour otherwise unchanged: same staleness predicate (`updated_at`, not `created_at` —
  see the docstring on `list_stale`), same cross-owner reach, same per-row CAS and the
  `ConflictException` / `NotFoundException` skip that lets replicas race safely.

## Not in scope

- Jitter across replicas' sweep ticks. Related, separately arguable, and not what the `LIMIT`
  fixes — file it separately if it is wanted.
- Any analytics emission on the requeue path. Story 14 deliberately emits nothing there.
- Retuning `session.py` pool settings.
