# Scheduling Adapter Test Template (arq)

## Test Class Rules

- **Task function tests** (unit-level): mock the usecase, call the task function directly with a fake `ctx` dict (`{"container": fake_container}`) and assert the usecase was invoked with the right request -- no real Redis needed.
- **Queue adapter tests** (`ArqJobQueue`): use `arq`'s `ArqRedis` against a real local Redis test instance (from `infra/.env`), or `arq.worker.Worker` in test mode with `burst=True` to process the queue once and exit.
- **Worker wiring tests** (verifies the job actually gets dispatched end-to-end): run the worker in burst mode (`arq.run_worker(WorkerSettings, burst=True)`) against a test Redis DB, enqueue a job, then poll (via `tenacity`, never bare `asyncio.sleep`) for the expected side effect through the usecase's fake port.
- Use class-level docstring with Gherkin-style description.

## Scheduling-Specific Failure Patterns

| Current Implementation | Expected Test Failure |
|----------------------|----------------------|
| Task function not registered in `WorkerSettings.functions` | Job stays queued forever -- polling assertion times out |
| Task function doesn't call the usecase | Fake port's captured calls list stays empty |
| Cron job missing advisory lock | Duplicate usecase invocations detected when running 2+ worker instances in the test |

## Reference (read before generating)

- Test setup: `backend/adapters/scheduling/tests/conftest.py`
- Existing test: `backend/adapters/scheduling/tests/test_generation_task.py`
- Production code: `backend/adapters/scheduling/src/`

## Test Configuration

Test conftest provides:
- A test Redis DB index (isolated from dev/prod data) via `infra/.env`
- `burst=True` worker mode for deterministic, non-hanging test runs
- Mock/fake usecase dependencies via `pytest-mock` -- scheduling tests verify wiring, not business logic

## Naming Convention

- Test file: `test_{task_name}_task.py`
- Test method: `test_should_{expected_behavior}`

## Key Paths

- Tests: `backend/adapters/scheduling/tests/`
- Production: `backend/adapters/scheduling/src/`
