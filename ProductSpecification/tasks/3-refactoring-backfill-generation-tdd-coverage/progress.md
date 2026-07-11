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
- [~] red-usecase
- [ ] green-usecase

### Step 3: DB storage adapter — persist & read generation (status + content)
- [ ] red-adapter db
- [ ] green-adapter db

### Step 4: REST adapter — POST creates pending, GET returns status/content
- [ ] red-adapter rest
- [ ] green-adapter rest

### Step 5: Provider integration — cover GigaChatProvider or explicitly isolate
- [ ] red-adapter generation_provider
- [ ] green-adapter generation_provider

### Step 6: Acceptance — happy-path create → pending → status → completed content
- [ ] red-acceptance
- [ ] green-acceptance
