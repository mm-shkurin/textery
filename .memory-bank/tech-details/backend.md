# Tech Details — Backend

## Status
No code written yet. `backend/` is empty. This file records what's decided vs. still
open before the first story can start.

## Decided
- **Language/framework:** Python + FastAPI.
- **Architecture:** Hexagonal (Ports & Adapters), mapped onto continue-framework's Clean
  Architecture layers: `domain` (zero framework deps) ← `usecase` (defines ports) ←
  `adapters` (REST/DB/email/... implement the ports) ← `application` (composition root).
- **Methodology:** strict TDD/ATDD via `/continue` — see
  [steerings/development-conventions.md](../steerings/development-conventions.md).

## Open — must resolve before the `python-fastapi-hex` tech profile can be authored
- ORM / persistence: SQLAlchemy vs raw asyncpg vs other?
- Migrations tool: Alembic vs other?
- DI approach: FastAPI's built-in `Depends()` vs a dedicated container
  (e.g. `dependency-injector`)?
- Test runner / mocking: pytest + what mocking library (unittest.mock, pytest-mock)?
- Coverage tool: coverage.py / pytest-cov?

Once these are answered, `.claude/tech/python-fastapi-hex/` (coding.md, tdd.md,
infrastructure.md, templates/) gets written, and
`ProductSpecification/technology.md`'s Backend section gets filled in from it — see
that file's current TODO markers.

## Entities / domain model
None yet — no story has gone through `/interview` → `/story` yet
(`ProductSpecification/stories.md` is still empty).
