# Story 1: Auto-generate: доклад — Backend Progress

Split out of `progress.md` on 2026-07-13 (Phase 6 of `_project_audit/CLEANUP_PLAN.md`) so
backend and frontend work don't collide on the same file. Owns: Backend, Integration,
Security, Load, and Infrastructure Scenarios (acceptance steps stay inline per scenario —
they aren't a separable layer). Narrative/decisions/Spec checklist live in `progress.md`;
`ProductSpecification/stories.md` is the cross-file rollup.

## Backend Scenarios (01_API_Tests.md)

### Scenario 1.1: Reject request with missing topic
- [x] red-acceptance
- [x] design
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery (rest) — Check 1 (ports): [S] no outbound port, rejects before persistence. Check 2 (exceptions): rest — ValidationException unmapped, no FastAPI app/exception handler exists yet. Check 3 (response shape): rest — placeholder http.server returns 501 instead of 400 `{"detail": "topic is required"}`. Checks 2+3 collapse into one rest pair. green-adapter rest must also introduce a minimal `RequestGeneration` usecase wrapping `Generation.create()` (controller must delegate to a usecase per coding-rules.md, none exists yet).
- [x] red-adapter rest
- [x] green-adapter rest
- [x] green-acceptance

### Scenario 1.2: Reject request with out-of-range volume
- [x] red-acceptance
- [x] design
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery — Check 1 (ports): [S] no outbound port, same as 1.1. Check 2 (exceptions): [S] `ValidationException` already mapped to 400 by the generic handler registered in 1.1's `green-adapter rest`. Check 3 (response shape): [S] router already forwards `volume_pages` through to `Generation.create`; response shape (400 + `{"detail": ...}`) matches acceptance expectation, same code path as 1.1. No adapter changes needed — only the acceptance test's skip marker (stale per agent-review finding) blocks green-acceptance.
- [x] green-acceptance — un-skipped only (no production code needed, adapter already sufficient per discovery above); 3/3 acceptance tests passed

### Scenario 1.3: Reject requirements/extra_wishes exceeding the length limit
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.4: Reject unsupported document type
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.5: Ignore server-owned fields in the request body
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.6: Ignore a client-supplied creation timestamp
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.7: Accept and reject requirements/extra_wishes length limits for Cyrillic text
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Valid request is accepted and queued without waiting on the LLM call
- [x] red-acceptance
- [x] design — see `decisions/persist-and-enqueue-architecture-decision.md`
- [x] red-usecase
- [x] green-usecase
- [x] adapters-discovery — Check 1 (ports): GenerationStorage has no adapter at all (`backend/adapters/db` doesn't exist yet) → needs `red-adapter db`/`green-adapter db` (SQLAlchemy model + Alembic migration for `generations` table with CHECK constraint per ADR, session/engine setup). GenerationQueue has no adapter at all (no arq module yet) → needs `red-adapter queue`/`green-adapter queue` (arq producer using `REDIS_URL`). Check 2 (exceptions): [S] scenario 2.1 is happy-path only, no new domain exception to map. Check 3 (response shape): REST router currently returns no body (201 only) but the already-red acceptance test expects `generation_id`/`status`/echoed fields/`created_at` in the body → needs `red-adapter rest`/`green-adapter rest`. Also `get_generation_usecase()` still does `return RequestGeneration()` with no args (will raise `TypeError` once real ports are wired) — must be updated to inject the real db/queue adapters.
- [x] red-adapter db — backfilled 2026-07-10 under P0-3's note, `backend/adapters/db/tests/`, verified genuinely red
- [x] green-adapter db — same backfill pass, real Postgres round-trip green
- [S] red-adapter queue — `NoOpGenerationQueue` is a deliberate no-op (known-debt #10/#11), no real arq producer exists to test; generation runs inline via FastAPI `BackgroundTasks` instead
- [S] green-adapter queue — see red-adapter queue skip reason
- [x] red-adapter rest — backfilled 2026-07-10, `test_generation_post_router.py`, verified genuinely red against a `NotImplementedError` handler stub. Correction to an earlier same-day note: the "echoed fields" expectation in this discovery note above was in fact still correct — the evening-demo `GenerationCreatedDto` had regressed to `generation_id`/`status`/`created_at` only, dropping the fields the original red-acceptance test (below) already expected. Fixed by extending the DTO with `topic`/`volume_pages`/`document_type`, not by narrowing the test.
- [x] green-adapter rest — same backfill pass, 201 + background-task enqueue verified against the corrected DTO shape
- [x] green-acceptance — un-skipped `test_should_accept_and_queue_valid_request_without_waiting_on_llm` (remove-marker-only), ran against a real running backend (uvicorn + local Postgres + fake provider). Backend acceptance suite: 4/4 passing.

### Scenario 2.2: An entirely Cyrillic request round-trips without corruption
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Replaying the same idempotency key does not create a duplicate generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.2: A redelivered background job does not reprocess an already-progressing generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: A pending generation reports its status without document content
- [x] red-acceptance — Task 3 Step 6 (2026-07-11/12) added a real top-level `acceptance/tests/backend/auto_generate_doklad/test_generation_lifecycle_acceptance.py`, verified genuinely red first, covering the pending-status leg of the 2.1→4.1→4.2 lifecycle
- [S] design — trivial pass-through (`GetGeneration.execute` already existed)
- [x] red-usecase — `TestGetGenerationStatus`, verified red against `NotImplementedError` stub
- [x] green-usecase — restored real implementation, 15/15 usecase suite green
- [x] adapters-discovery — REST `GET /generations/{id}` backfilled 2026-07-10: `test_generation_get_router.py`, verified red against a `NotImplementedError` handler stub. DB storage adapter (`get`) already covered under P0-3's backfill note.
- [x] green-acceptance — Task 3 Step 6: skip marker removed, full backend acceptance suite green (5 passed, 0 skipped) against the wired backend (fake provider, local Postgres)

### Scenario 4.2: A completed generation includes the document content
- [x] red-acceptance — same Task 3 Step 6 lifecycle test, covering the completed-with-content leg
- [S] design — trivial pass-through
- [x] red-usecase — `TestGetGenerationCompleted`, same backfill pass
- [x] green-usecase — same backfill pass
- [x] adapters-discovery — same REST backfill pass, `TestGetGenerationCompleted` (router)
- [x] green-acceptance — same Task 3 Step 6 green run as 4.1

### Scenario 4.3: Requesting a non-existent generation reports not found
- [S] red-acceptance — backfilled at usecase+rest layer only 2026-07-10, see below; no top-level `acceptance/` black-box test yet
- [S] design — trivial pass-through
- [x] red-usecase — `TestGetGenerationNotFound`, same backfill pass
- [x] green-usecase — same backfill pass
- [x] adapters-discovery — same REST backfill pass, `TestGetGenerationNotFound` (router)
- [~] green-acceptance — same gap as 4.1

### Scenario 5.1: A permanent generation-provider error fails fast without exhausting retries
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: A transient generation-provider error is retried and can still succeed
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: Exhausting the retry budget fails the generation, never leaves it stuck
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.4: A generation abandoned by a dead worker is eventually reconciled
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.5: A generation still within its normal processing window is not prematurely reconciled
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.6: A worker's genuine completion is never clobbered by a concurrent reconciliation sweep
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1: Listing returns generations across all callers, most recent page first
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.2: Paginating with a cursor is stable while new generations are being created
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.3: The list caps its page size even when far more generations exist
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.4: Generations with the same creation timestamp still list in a stable order
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Integration Scenarios (06_Integration_Tests.md)

### Scenario 1.1: A successful provider call produces a completed document
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 1.2: The requested volume converts to a pinned, tested prompt budget for Cyrillic text
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Permanent and transient provider errors are handled differently
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.2: A malformed or empty provider response is treated as a failure
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.3: Each failure family is recorded with a distinguishable category server-side
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: A hung provider call is cancelled at the job deadline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: Redelivering the same background job does not call the provider twice
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.2: Redelivering a job for an already-failed generation does not reprocess it
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: The document and the completed status commit together, never one without the other
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: A commit failure after a successful provider call does not trigger a duplicate call
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1: The bounded retry sequence fits within the job's overall deadline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.1: A permanently failing generation does not block other generations from completing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.1: Concurrent retries after a shared transient outage do not all retry at the same instant
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Security Scenarios (05_Security_Tests.md)

### Scenario 1.1: Injection payloads in free-text fields are stored and returned safely
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Document content and echoed input are served as escaped text
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Server-owned fields cannot be set by the client
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: Oversized free-text fields are rejected before reaching the generation provider
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: Generation identifiers are not predictable across consecutive creations
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 6.1: A generation-provider failure never leaks credentials or raw upstream detail
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 7.1: A flood of submissions cannot drive unbounded concurrent provider calls
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 8.1: A malformed idempotency key is rejected, not passed through
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 9.1: A request with deeply nested or oversized JSON is rejected before parsing cost balloons
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Load Scenarios (03_Load_Tests.md)

### Scenario 1.1: Generation submission sustains the configured throughput baseline
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: A burst of submissions does not exceed the worker concurrency ceiling
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Throughput recovers after a burst subsides
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

## Infrastructure Scenarios (04_Infrastructure_Tests.md)

### Scenario 1.1: Generation submission fails cleanly when the database is unavailable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 2.1: Pending generations resume processing after the database recovers
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 3.1: Generation fails gracefully when the generation provider is unreachable
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 4.1: The application fails fast at boot when required generation-provider config is missing
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.1: The reconciliation sweep does not double-process the same stale generation
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.2: A generation whose job was silently never enqueued is still reconciled
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance

### Scenario 5.3: Resource usage returns to baseline after repeated failure and cancellation handling
- [ ] red-acceptance
- [ ] design
- [ ] red-usecase
- [ ] green-usecase
- [ ] adapters-discovery
- [ ] green-acceptance
