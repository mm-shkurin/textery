# Backend audit remediation (2026-07-10)

Direct remediation pass against `backend/` findings from the external code-quality
grading prompt, done at the user's request **outside** the normal story-scenario TDD
lifecycle — no red/green ceremony, not tracked as checkboxes in `progress.md`. Same
spirit as `frontend-audit-remediation.md`, backend-scoped counterpart. Run as two
parallel Claude Code sessions (A and B) against the same working tree/branch (`dev`)
since `backend/` turned out **not** to be its own git repo — `git rev-parse
--show-toplevel` from inside `backend/` resolves to the `textery` root.

**Score before:** 2.0/3.0. Not yet re-audited after remediation. 9 of 10 findings
closed (all except finding 5, auth/ACL — explicitly deferred). Both sessions'
full test suites green after merge: usecase 21/21, domain 8/8,
generation_provider 3/3, db 7/7 (migration chain `a1b2c3d4e5f6 → b2c3d4e5f6a7 →
c3d4e5f6a7b8` applied), rest 6/6.

## Findings from the audit (10 total)

1. `NoOpGenerationQueue` + FastAPI `BackgroundTasks` — in-process only, lost on
   worker crash/restart. Violates the multi-instance no-in-memory-state rule.
2. `gigachat_provider.py` — credentials env var never validated; unset produces a
   literal `"Basic None"` header instead of a startup failure.
3. Raw provider exception text leaked to the API client via `error_message`.
4. `generation_storage.update()` — read-then-write with no optimistic locking;
   concurrent status transitions could silently lose writes.
5. No auth/ACL on `POST /generations` / `GET /{id}` — any caller can trigger
   cost-incurring GigaChat calls or read any generation by id.
6. Status constants duplicated between `generation_model.py`'s `CheckConstraint`
   and `generation.py`'s domain constants.
7. Inconsistent typing style (`X | None` vs `Optional[X]`) across the same codebase.
8. No sweep/reconciliation job — a generation stuck mid-flight had zero automated
   recovery path.
9. No index on `generations.status`, despite it being the natural filter column for
   any future pending-sweep query.
10. No length cap on `topic`/`requirements`/`extra_wishes` anywhere (domain, DTO, or
    DB) — unbounded payload forwarded to an external LLM (cost/DoS vector).

User split remediation across two sessions to run in parallel; **auth (finding 5)
was explicitly deferred**, not assigned to either session this pass.

## Session A — reliability/infra (findings 1, 8, 9)

Three commits on `dev`:

| Commit | Summary |
|---|---|
| `f556a4c` | `Generation.requeue()` domain method + `RequeueStaleGenerations` usecase (`backend/usecase/src/generation/requeue_stale_generations.py`) — finds pending/in_progress rows past a staleness threshold via `GenerationStorage.list_stale()` and resets them to pending. Usecase does not call `GenerateDocument` directly (no usecase-calls-usecase) — it only owns the state transition. |
| `0c15046` | `ix_generations_status` index (migration `c3d4e5f6a7b8`) + `SqlAlchemyGenerationStorage.list_stale()`. Landed together with Session B's optimistic-locking version column since both touched `generation_storage.py`/`generation_model.py` concurrently — could not be split file-by-file. |
| `fe288ed` | Wired the sweep into `application/src/app/main.py` via a `lifespan` context manager running an asyncio loop every 60s, calling `container.run_stale_generation_sweep()` → `RequeueStaleGenerations.execute()` → re-triggers `GenerateDocument.execute()` per recovered id (application-layer orchestration, not usecase-to-usecase). `NoOpGenerationQueue`'s docstring corrected to explain durability now comes from the sweep, not the queue. |

Tests: 4 new usecase tests (`test_requeue_stale_generations_usecase.py`, Statements
DSL) + 2 new storage tests (`TestListStale`). `usecase` suite 25/25, `db` suite 7/7
passing after applying the migration chain to the local postgres test DB.

**Migration revision collision:** both sessions independently generated migration
revision `b2c3d4e5f6a7` from the same `down_revision` (`a1b2c3d4e5f6`). Session A's
index migration was renamed to `c3d4e5f6a7b8` and re-parented onto Session B's
`b2c3d4e5f6a7` (version column) to keep a single linear chain:
`a1b2c3d4e5f6 → b2c3d4e5f6a7 → c3d4e5f6a7b8`.

## Session B — correctness/data integrity (findings 2, 3, 4, 6, 7, 10)

Ran concurrently in the same working tree. Six commits on `dev`, each with its own
tests, plus a retroactive task record:

| Commit | Finding | Summary |
|---|---|---|
| `901141b` | 2 | `gigachat_provider.py` fails fast (new domain exception) when `GIGACHAT_CREDENTIALS` is unset/blank, instead of sending a literal `"Basic None"` Authorization header |
| `4bf5127` | 3, 7 | `generate_document.py` no longer persists raw `ProviderError` text into `error_message`/the REST response — stores a generic message, logs the full error server-side; also normalizes `Optional[X]` typing style to match the rest of the codebase |
| `787a1a8` | 6 | `generation_model.py`'s `ALLOWED_STATUSES` now derives from `generation.py`'s `PENDING_STATUS`/`IN_PROGRESS_STATUS`/`COMPLETED_STATUS`/`FAILED_STATUS` instead of a third independent hardcoded copy |
| `d4c7f97` | 10 | `Generation.create()` rejects topic > 500 chars, requirements/extra_wishes > 2000 chars each (provisional caps, domain-level `ValidationException`) |
| `301a757` | 4 | `version` column (migration `b2c3d4e5f6a7`) + `SqlAlchemyGenerationStorage.update()` raises `ConflictException` on a stale version instead of silently overwriting a concurrent update |
| `2e0057c` | — | documents the six-part fix as task `ProductSpecification/tasks/2-refactoring-generation-hardening/` |

All six findings assigned to Session B confirmed closed by direct commit inspection
after both sessions' work merged.

## Explicitly deferred (not assigned to either session)

- **Finding 5 (auth/ACL)** — no auth system exists in `backend/` at all (no `User`
  model, no JWT, no `current_user` — confirmed via grep before starting). Building
  one from scratch is a separate architectural decision, not a same-session fix.
  User chose to skip it this pass rather than stub a minimal `X-User-Id` header or
  commit to full login/token infrastructure.

## Closure (2026-07-13, docs cleanup session)

Never re-audited after the single remediation pass — score stands at its **pre-fix
2.0/3.0 baseline**, unrefreshed. 9/10 findings closed by direct commit inspection
(see Session A/B tables above); finding 5 (auth/ACL) explicitly deferred, no auth
system exists in `backend/` at all. Re-running the external grading prompt is a
separate exercise, not a documentation fix, so it's out of scope for this
docs-cleanup session — flagging this explicitly instead of leaving the score
looking silently unfinished.

## Where this sits relative to the story

Touched files (`domain/src/generation/generation.py`,
`usecase/src/generation/*`, `usecase/src/adapters/generation_storage.py`,
`adapters/db/src/{access,model}/generation/*`, `application/src/app/{container,main}.py`)
are all part of Story 1's Backend/Integration Scenarios (see `progress.md`). This
pass hardens generation lifecycle reliability and data-integrity guarantees
retroactively without reopening the formal per-scenario checkboxes.
