# Python/FastAPI/Hexagonal TDD Idioms

Tech binding for `tdd-rules.md`. Load alongside the universal rules.

## Test Disable Marker

- pytest: `@pytest.mark.skip(reason="RED: ...")` decorator on test functions/classes
- Referenced as "test disable marker" in universal rules
- In RED: add `@pytest.mark.skip` after validating prediction
- In GREEN: remove `@pytest.mark.skip` (the only test modification allowed)
- In commit discipline: RED commits include skipped tests

## Test Description

- Use `class TestFeatureName:` with descriptive method names `test_should_{expected_behavior}`
- Add a module-level or class-level docstring to document the scenario in plain English
- Test class DSL should match the abstraction level of its docstring

## Stub Pattern

- `raise NotImplementedError()` for real adapter stubs in RED
- Fakes are functional (not stubbed) — only real adapters use this pattern

## Domain Stub Examples

- If a test asserts `Column.empty("To Do")`, Column needs only a `name` field — not a `tasks: list[Task]` field and a separate `Task` class with 4 fields
- When a domain constructor changes (e.g., adding `GenerationStatus` to `Generation`), patch callers with enum defaults like `GenerationStatus.PENDING`

## Build Green in RED — Forbidden Changes

- Never add SQLAlchemy model columns or `__table_args__` changes during RED
- Never add Alembic migrations during RED
- Never add new declarative model fields during RED
- These are implementation, not plumbing — they belong in GREEN

## GREEN Phase Artifacts

- Production code, Alembic migrations (`alembic revision --autogenerate`, `alembic upgrade head`), SQLAlchemy models, async queries

## Async Test Execution

- `pytest-asyncio` runs `async def test_...` functions. Set `asyncio_mode = "auto"` in `pytest.ini`/`pyproject.toml` so test functions don't need `@pytest.mark.asyncio` on every test.
- Fixtures that yield an `AsyncSession` or an `arq` connection must themselves be `async def` fixtures (`@pytest_asyncio.fixture`).
- This applies across every layer that touches the async engine or async usecases — usecase tests, `db` adapter tests, `rest` adapter tests calling `async def` usecases, acceptance tests.

## Coverage Tool

- `pytest-cov` (coverage.py) for Python code coverage
- Reports in `htmlcov/` and `.coverage` (XML via `--cov-report=xml:coverage.xml`)
- Run per-module: domain files checked against usecase coverage, adapter files checked against adapter coverage
- Scan touched files across `backend/*/src/` and `backend/adapters/*/src/`

## Test Filter Flag

- pytest: `-k "ClassName"` or `pytest path/to/test_file.py::TestClassName`
- Example: `pytest backend/usecase/tests/test_generation.py::TestCreateGeneration`
- Acceptance: poll output file for `FAILED|PASSED|ERROR` markers

## 3-Tier Test Architecture — Python Specifics

### Test Class
- See universal 3-Tier rules in `tdd-rules.md` (no assertions, no control flow, no private members in test class)
- Python-specific: private functions are prefixed with `_` (e.g., `_helper`) — these indicate a violation of the universal rule

### Scope
- Use a `@dataclass(frozen=True)` with a `@classmethod` builder that accepts `**overrides`
- Implementation: class with `DEFAULTS` dict and `@classmethod builder(cls, **overrides) -> Scope`
- Example: `scope = GenerationScope.builder(document_type="доклад")` — returns a `GenerationScope` with all defaults except `document_type`
- Default values via dict merge: `{**cls.DEFAULTS, **overrides}`
- All fields readonly via `frozen=True` — scopes are immutable value objects

## Test Data & Isolation — Python/FastAPI Specifics

- DB adapter tests: async fixture opens an `AsyncSession` inside a transaction, rolls back on teardown (`async with engine.connect() as conn: async with conn.begin() as trans: ...; await trans.rollback()`) — no truncation, no separate test database recreation per test.
- REST adapter tests: `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` calling the FastAPI app directly (no running server needed).
- Mocking: `pytest-mock`'s `mocker.Mock()` / `mocker.patch()` (wraps `unittest.mock`). Reset is automatic per-test via the `mocker` fixture — no manual `reset_mock()` needed between tests.
- Fakes: plain Python classes implementing port `Protocol`s with in-memory `dict`/`list` storage. Async ports get `async def` fake methods that return immediately (no real I/O).

## Assertion Library (pytest assertions)

- Strict equality: `assert actual == expected`
- Non-null (last resort): `assert actual is not None`
- Timestamp bounds: `assert actual > now - timedelta(seconds=30)`
- Exception assertions: `with pytest.raises(ValidationException):`
- Async exception: `with pytest.raises(ValidationException): await usecase.execute(request)`
- Recursive comparison: `assert actual == expected` — Python `==` on dataclasses does deep structural comparison by default
- List comparison: `assert set(actual) == set(expected)` for unordered, `assert actual == expected` for ordered
- Reserve per-field assertions only when custom comparators or field exclusions are needed

## Async Wait Pattern

- **Waiting for side-effect** (e.g., an `arq` job has picked up a generation request and moved it to `IN_PROGRESS`): `tenacity` with assertion-based polling:
  ```python
  from tenacity import retry, stop_after_delay, wait_fixed

  @retry(stop=stop_after_delay(5), wait=wait_fixed(0.1))
  def assert_eventually():
      assert actual_value() == expected
  ```
- **Negative assertion ("nothing happened")**: poll for a duration, asserting the condition holds throughout:
  ```python
  from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type

  @retry(stop=stop_after_delay(2), wait=wait_fixed(0.2), retry=retry_if_exception_type(AssertionError))
  def assert_still_true():
      assert condition_holds()
  # Invert: if it ever raises, the condition changed
  ```
- Never use bare `time.sleep()` or `await asyncio.sleep()` as a wait — always use `tenacity` with assertions

## Test Review Grep Patterns

Grep patterns for the test-review-agent checklist. Each entry maps to a checklist item number.

| # | Check | Grep pattern |
|---|-------|-------------|
| 2 | Loose string assertions | `in actual\|is not None\|!= None\|assert len` |
| 3 | Range/direction checks | `> \|< \|>= \|<= \|between` |
| 4 | Loose mock matchers | `call_args\|ANY\|mock.ANY` |
| 6 | Partial collection coverage | `\[0\]` |
| 12 | Assertions in test class | `assert \|pytest.raises` |
| 21 | Calculated expected values | `math\.\|ceil\|floor\|% \|// \|len(.*) [*/]` |
| 23 | Private functions in test class | `def _` |
| 26 | HTTP client code in acceptance Statements | `httpx\.\|AsyncClient\|client.get\|client.post\|client.put\|client.delete` |

## Test Clock

- Inject a `Clock` protocol; use a `FakeClock` in tests with `advance(seconds: float)` method
- Example: `fake_clock.advance(31 * 24 * 3600)` to expire a 30-day session
