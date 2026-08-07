# Audit Log

Independent-auditor passes over `backend/`, judging only current file and Git
state. Each iteration re-ran the gates from scratch rather than trusting the
previous pass.

## Iteration 1 — Score: 2.0 / 3.0

### Findings

- `ruff format --check .` failed on 16 files; the `lint` CI job was red on every push regardless of content.
- `mypy` reported 34 errors across 12 files; the `types` CI job was red, so neither of its two invocations gated anything.
- `usecase/src/generation/generate_document.py` passed `int | None` to `PromptRequest.volume_pages` and `str | None` to `topic` — a real nullability hole, not a missing annotation.
- `adapters/rest/src/dto/project/project_response_dto.py` built `ProjectStatus(...)` from `object` and passed raw `str` where the `ProjectStatus`/`ProjectKind` enums were declared.
- `domain/tests/generation/test_prompt_type_coverage.py:82` had a comment wrapping so a line began `# type: `; mypy read it as a type comment, errored, and silently stopped checking the rest of the file.
- 8 files exceeded the 200-line hard limit in `.claude/rules/coding-rules.md`, one of them production code.
- `FakeGenerationProvider.generate` still took the `Generation` entity after scenario 2.1 narrowed the port to `prompt: str`; `FakeGenerationStorage` was missing two port methods entirely.
- `usecase/tests/statements/generation_prompt_failure_assertions.py` had an empty-bodied function declared to return a value.

### Fixed

- `fix(types)` — production nullability and enum-boundary holes; four bare signatures the `--disallow-incomplete-defs` pass rejected.
- `test(generation)` — both generation doubles realigned with their ports.
- `test(types)` — the type-comment hole, the `AsyncIterator`/`AsyncGenerator` mismatch, two kwargs-bundle annotations, the empty body, and one deliberate `type: ignore` with its reason.
- `style(backend)` — the 17 files failing the formatter.

### Blockers carried forward

- The 200-line limit, still unenforced and still violated 8 times.
- Two distinct classes named `FakeGenerationStorage`.

### Note

A concurrent session committed this iteration's in-progress work into an
unrelated frontend commit (`20b540de`). It was unpushed and at HEAD; with the
user's approval it was split back into its own commits. No work was lost.

## Iteration 2 — Score: 2.5 / 3.0

### Findings

- 8 files over the 200-line limit; no gate behind the rule, unlike every other stated rule in the repository.
- `FakeGenerationStorage` named two different classes with different constructors and different subsets of the port, depending on the import line.

### Fixed

- `refactor(generation)` — the inline duplicate deleted; the conversion tests now
  run against the shared double that mirrors the real adapter's CAS conflicts and
  owner predicate, seeded through `a_generation_storage(*generations)`.
- `ci(lint)` — `scripts/check_file_size.py`, wired into the `lint` job. It asks
  git for the file list so its answer does not depend on the machine's stray
  files, and excludes Alembic's generated migrations to match the exclusions
  pyproject.toml already gives them.
- `refactor(backend)` — all eight files split along seams they already had.
  Test count unchanged: 68 collected in the db suite before and after, identical
  node ids modulo one file rename.

### Found while splitting

The CAS tests resolved their own database URL, defaulting to `.../textery` — the
application's database, not `textery_test` — while their teardown TRUNCATEs every
table. That is the 2026-08-06 data-loss incident's exact shape, and the guard
added in response was the one thing those tests bypassed. They now go through it.

## Iteration 3 — Score: 2.5 / 3.0

### Outstanding blockers

- No CI job runs the `acceptance/` suite; the black-box HTTP tests never execute automatically.
- `README.md` has no development-setup section covering `TEST_DATABASE_URL`. On a fresh checkout 70 tests skip with nothing saying how to unskip them.
- `CHANGELOG.md` was last updated 2026-07-31 and records none of the commits since.
- `requirements.txt` does not separate runtime from development dependencies — `pytest`, `mypy`, `ruff` and `pip-audit` install into production images.

None of these are code-quality defects in the shipped source; all four are
process and packaging gaps.

## Iteration 4 — Score: 2.5 / 3.0 (confirmation)

Re-ran every gate from a clean invocation. Score held across two consecutive
passes, so the loop terminates here.

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 395 files already formatted |
| `mypy` | 385 source files, no issues |
| `mypy --disallow-incomplete-defs` (src roots) | 153 files, no issues |
| `python scripts/check_file_size.py` | exit 0 |
| `pytest` | 777 passed, 70 skipped |

The 70 skips are the Postgres-backed adapter tests. They are not skipped in CI —
the `test` job installs Postgres, runs the migrations and executes them there.
They could not be executed locally during this audit, so their *collection* was
verified (imports and fixture wiring resolve) but their *execution* was not.

## Iteration 5 — Score: 2.5 / 3.0

### Findings

- `infra/docker/backend.Dockerfile` installed the whole `requirements.txt` into the production image, so `pytest`, `pytest-cov`, `pytest-mock`, `ruff`, `mypy` and a stubs package shipped to production alongside FastAPI.
- `requirements.txt` did not separate runtime from tooling, which cost the `audit` job its meaning: `pip-audit` answered "is anything in this file vulnerable" rather than "is what we deploy vulnerable".
- `README.md` never named `TEST_DATABASE_URL` or the required `textery_test` database. On a fresh checkout 70 tests skipped, and "skipped" reads as "not applicable to me" rather than "you have not finished setting up".
- `CHANGELOG.md` had stopped at 2026-07-31 and recorded none of the eight commits since, including the stretch where `lint` and `types` were red.
- `acceptance/` declares no dependencies anywhere, though `acceptance/conftest.py:10` imports `selenium`. **Not fixed** — `acceptance/` is a separate top-level module and is not part of the repository this directory publishes as.

### Fixed

- `build(deps)` — runtime/dev split. `audit` deliberately stays on the runtime
  file; `types` and `test` move to the dev file, which starts with
  `-r requirements.txt`. Both CI pip caches now key on both files. Nothing was
  unpinned by the split.
- `docs(backend)` — README setup section for the test database, including why the
  name must contain `test`; changelog Unreleased refilled, with the production
  defects stated as defects rather than as tidying.

## Iteration 6 — Score: 2.5 / 3.0

### Findings

- `OAUTH_FAKE_AUTHORIZE_URL` is read by `application/src/app/container/oauth_wiring.py:77` and appears nowhere in `.env.example`, whose own header claims to document every variable the backend consumes. The failure mode is not an error but a default quietly applying in an environment that meant to override it.

### Fixed

- `test(config)` — the variable documented, plus a test that scans the production
  roots for environment reads and fails on any the file does not declare, with a
  second test guarding it against scanning nothing. Verified by deleting the new
  entry and watching the check go red on exactly `['OAUTH_FAKE_AUTHORIZE_URL']`.

### Swept clean, no findings

No `TODO`/`FIXME`/`HACK` markers anywhere in the source. No inward-dependency
violations (`domain` and `usecase` import no adapter module). No magic numbers in
the production branches sampled. Layer coverage is 87% locally and 98% in CI --
the difference is entirely the 70 Postgres-backed tests, whose uncovered lines
are all under `adapters/db/src`.

## Final state

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 396 files already formatted |
| `mypy` | 386 source files, no issues |
| `mypy --disallow-incomplete-defs` (src roots) | 153 files, no issues |
| `python scripts/check_file_size.py` | exit 0 |
| `pytest` | 779 passed, 70 skipped |
| production dependencies | 13, down from 20 |
| tracked secrets or build output | none |

Six iterations. Score moved 2.0 -> 2.5 at iteration 2 and held there through four
further passes; the remaining gap to 3.0 is process work outside this directory
(no CI job runs `acceptance/`, which is not part of the repository `backend/`
publishes as, and which declares no dependencies of its own).
