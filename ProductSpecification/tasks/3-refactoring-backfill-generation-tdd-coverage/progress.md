# Task 3: Backfill TDD coverage for the generation vertical slice -- Progress

Type: refactoring

## Spec
- [x] spec

## Fix

Each step: run `/test-coverage` on the layer first to locate genuine gaps, then
add only the missing red/green coverage. Behavior must not change — new tests
characterize the code as it stands today. Confirm a layer already covered and
move on rather than rewriting existing tests.

### Step 1: Usecase — RequestGeneration creates pending + enqueues (Scenario 2.1)
- [S] red-usecase — already covered: `request_generation.py` at 100% line+branch (pytest-cov `--cov=generation --cov-branch`, 2026-07-12). `TestGenerationUsecaseHappyPath.test_should_return_pending_generation_and_enqueue_job` (runs + PASSES, not skipped) strictly characterizes status='pending', id is UUID, created_at within submit window, all 5 request fields, save-exactly-once, enqueue-exactly-once, save-before-enqueue ordering. No genuine gap; adding a test would rewrite existing coverage (task rule: confirm covered and move on).
- [S] green-usecase — nothing to implement: red found no gap (layer already 100% covered).

### Step 2: Usecase — GetGeneration returns status; completed returns content (4.1 / 4.2)
- [S] red-usecase — already covered: `get_generation.py` at 100% line+branch (pytest-cov, 2026-07-12). GetGeneration is a pass-through (`return storage.get(id)`); Scenarios 4.1/4.2/4.3 characterized by TestGetGenerationStatus / TestGetGenerationCompleted / TestGetGenerationNotFound (all run + PASS), strictly asserting status='pending'+content=None (4.1), status='completed'+content==expected (4.2), None for unknown id (4.3). No gap; adding a test would rewrite existing coverage.
- [S] green-usecase — nothing to implement: red found no gap (layer already 100% covered).

### Step 3: DB storage adapter — persist & read generation (status + content)
- [S] red-adapter db — already covered: `generation_storage.py` at 100% line+branch and `generation_model.py` at 100% (pytest-cov against local Postgres 16, 2026-07-12). 7 passing tests characterize the full SqlAlchemyGenerationStorage surface: TestSaveAndGet (round-trip all fields), TestGetUnknownId (None), TestUpdate (persist status+content — the Step 3 target), TestUpdateUnknownId (NotFoundException), TestUpdateConcurrentConflict (ConflictException / optimistic lock), TestListStale (include stale / exclude fresh). No gap; adding a test would rewrite existing coverage.
- [S] green-adapter db — nothing to implement: red found no gap (storage + model both at 100%).

### Step 4: REST adapter — POST creates pending, GET returns status/content
- [x] red-adapter rest — scenario behaviors (POST 201 pending, GET pending/completed/404, POST 400 missing-topic) were already 100% covered; the only gap was `generation_router.py` at 89% (lines 15/19/23 = the three unwired dependency-provider guards). Added `test_generation_router_wiring.py` (parametrized, 3 cases) asserting each `get_*_usecase()` raises `NotImplementedError("wired by the application composition root")` — closes router to 100% line+branch. Characterization of existing behavior → GREEN on first run, no production change. /test-review PASS.
- [S] green-adapter rest — nothing to implement: the red characterization test is GREEN on first run and the full REST generation module (router + both DTOs) is at 100% line+branch (pytest-cov, 8 passed, 2026-07-12). No production code to add.

### Step 5: Provider integration — cover GigaChatProvider or explicitly isolate
- [x] red-adapter generation_provider — took the **cover** option. Existing test covered only the constructor; `gigachat_provider.py` was 65% (generate() lines 35-50 + _fetch_token() 53-63 untested) and `fake_provider.py` unimported (0%). Added `test_gigachat_provider_generate.py` (stubs the httpx boundary via pytest-mock) characterizing the two-call flow: token fetch (Basic creds + scope + RqUID uuid4), Bearer wiring, exact prompt + completions body, and `httpx.HTTPError → ProviderError(str(error))`; plus `test_fake_provider.py` (returns exact `FAKE_DOKLAD_TEXT`). Closes provider package to 100% line+branch. Characterization → GREEN on first run, no production change. /test-review tightened assertions (full-dict body + token-call auth). The **live** GigaChat network path stays out of CI (stub only); CI runs with GENERATION_PROVIDER=fake.
- [S] green-adapter generation_provider — nothing to implement: the red characterization tests are GREEN on first run and the provider package (`gigachat_provider.py` + `fake_provider.py`) is at 100% line+branch (pytest-cov, 6 passed, 2026-07-12). No production code to add.

### Step 6: Acceptance — happy-path create → pending → status → completed content
- [~] red-acceptance
- [ ] green-acceptance
