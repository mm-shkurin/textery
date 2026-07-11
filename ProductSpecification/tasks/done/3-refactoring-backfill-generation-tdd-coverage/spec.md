# Task 3: Backfill TDD coverage for the generation vertical slice

Type: refactoring

## Problem

The generation flow (`POST /generations` → pending → background provider call →
`GET /generations/{id}` → completed with content) was built under deadline
pressure partly **off-framework** — the evening-demo slice (2026-07-09) and the
P0 backfill (2026-07-10) landed real DB and REST adapters, the usecase, and a
live GigaChat provider without the full red→review→green→coverage TDD cycle for
every layer (see `stories/01-auto-generate-doklad/progress.md`, known-debt #10).

Some coverage was already backfilled (P0-3/4/5: `test_generation_lifecycle_usecase.py`,
green-acceptance 4/4). What remains is uneven: the happy-path acceptance flow,
the DB/REST adapters, and the provider boundary were not all driven through the
framework, so there is no guarantee every behavior below is characterized by a
strict, coverage-verified test.

## Solution

Bring the **existing** implementation under the framework by adding
characterization tests for current behavior — **no behavior change, no
redesign, no adapter replacement, no new features.** Each step first runs
`/test-coverage` against the layer to find genuine gaps, then adds only the
missing red/green coverage; layers already fully covered are confirmed and left
alone.

Behaviors to characterize:
1. `POST /generations` with a valid request creates a **pending** generation and
   enqueues the job without waiting on the provider (Scenario 2.1).
2. `GET /generations/{id}` returns status for a pending generation without
   document content (Scenario 4.1).
3. A completed generation returns the document content (Scenario 4.2).
4. Provider integration is **covered** (isolated `GigaChatProvider` adapter test
   against a stubbed HTTP boundary) **or explicitly isolated** (real flows run
   against `FakeProvider`; the live GigaChat path stays out of automated CI and
   is documented as such). The `NoOpGenerationQueue` stays a deliberate no-op
   (known-debt) — nothing to test there.

Explicitly out of scope: retry/error-handling changes (Task 1), any new
validation contract, frontend scenarios, and the queue adapter.

## Key Files

Production code — **characterized, not modified**:

- backend/usecase/src/generation/request_generation.py
- backend/usecase/src/generation/get_generation.py
- backend/usecase/src/generation/generate_document.py
- backend/adapters/db/src/access/generation/generation_storage.py
- backend/adapters/rest/src/router/generation/generation_router.py
- backend/adapters/generation_provider/src/provider/gigachat_provider.py
- backend/adapters/generation_provider/src/provider/fake_provider.py

Test code — audited and extended to fill gaps:

- acceptance/tests/backend/auto_generate_doklad/ (happy-path create/status/content)
- backend/usecase/tests/generation/test_generation_usecase.py
- backend/usecase/tests/generation/test_generation_lifecycle_usecase.py
- backend/adapters/db/tests/access/generation/test_generation_storage.py
- backend/adapters/rest/tests/router/generation/test_generation_post_router.py
- backend/adapters/rest/tests/router/generation/test_generation_get_router.py
- backend/adapters/generation_provider/tests/provider/test_gigachat_provider.py
