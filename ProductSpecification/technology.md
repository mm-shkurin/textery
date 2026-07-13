# Technology Profile

## Methodology

This project follows the TDD/ATDD + Clean Architecture methodology described in:
- https://habr.com/ru/articles/1023094/
- https://habr.com/ru/articles/1023998/

Practically this means: strict red-green-refactor via `/continue`, ATDD chain
(red-acceptance → red-usecase → green-usecase → adapters → green-acceptance),
mandatory quality gates (test-review, coverage, refactor) before every commit,
and `progress.md` per story as the persistence mechanism across context resets.

tech-profile:
  backend: python-fastapi-hex
  frontend: react-ts
  css: plain-css
  browser-testing: selenium

## Backend

| Concern | Technology |
|---------|-----------|
| Language | Python 3.12 |
| Framework | FastAPI |
| Architecture | Hexagonal (Ports & Adapters), mapped onto Clean Architecture layers |
| ORM | SQLAlchemy 2.0 (async engine) |
| Migrations | Alembic |
| Database | PostgreSQL |
| Task queue | FastAPI `BackgroundTasks` + periodic DB-based sweep (reconciles stale/orphaned generations) — `arq`+Redis was the original plan (`ExpectedLoad.md`) but isn't implemented; Redis is still provisioned in `infra/docker-compose.yml`/CI as a placeholder for a future move to `arq`, unused by current code |
| DI | FastAPI `Depends()` + manual composition root (`container.py`) — no DI framework |
| Generation engine | GigaChat (Sber) — direct `httpx` HTTP client (`backend/adapters/generation_provider/src/provider/gigachat_provider.py`) with a custom Russian trust CA bundle (`russiantrustedca.pem`). OpenRouter/Claude was the original plan, superseded 2026-07-09 (known-debt #11) |
| HTTP client (other) | `httpx` (async) |
| Auth (story 7+) | JWT (`PyJWT`) + Yandex ID / VK ID OAuth (no Google) |

## Frontend

| Concern | Technology |
|---------|-----------|
| Language | TypeScript |
| Framework | React 18 |
| Build tool | Vite |
| Test runner | Vitest |
| HTTP mocking | `vi.mock()` (native Vitest) — MSW was the original plan, never installed |
| Linter | oxlint (`.oxlintrc.json`) |

## CSS

Plain CSS — decided 2026-07-07. The already-regenerated mockups
(`ProductSpecification/stories/01-auto-generate-doklad/mockups/`) are hand-written CSS
with custom properties (`:root { --bg-page: ...; --accent-gradient: ...; }`), not
Tailwind utility classes — porting them 1:1 into the React app is faster than
translating to Tailwind under this deadline. Revisit post-sprint-1 if the design system
grows enough to want a utility framework.

## Browser Testing

Selenium — per tech-lead guidance 2026-07-07 (see `.memory-bank/tasks/known-debt.md`,
now-closed #1).

## Testing (Backend)

| Concern | Technology |
|---------|-----------|
| Test runner | pytest |
| Async test support | pytest-asyncio (`asyncio_mode = auto`) |
| Mocking | pytest-mock |
| Coverage | pytest-cov (coverage.py) |
| REST test client | httpx.AsyncClient + ASGITransport (in-process, no running server) |

## Infrastructure

| Concern | Technology |
|---------|-----------|
| Containerization | Docker / docker-compose (provisioned by the separate `infra/` harness — see `infra/architecture.md`) |
| Database | PostgreSQL |
| Cache / queue | Redis — provisioned, not used by current code (see Task queue row above) |

## Conventions

### Backend

| Concern | Convention |
|---------|-----------|
| Test skip marker | `@pytest.mark.skip(reason="RED: ...")` |
| Not-implemented marker | `raise NotImplementedError()` |
| Dev command | `uvicorn app.main:app --reload --port $BACKEND_PORT` |
| Worker command | none — generation runs inline via `BackgroundTasks` in the ASGI process; `arq backend.application.worker.WorkerSettings` was the planned command, not yet needed |
| Test command | `pytest backend/` |
| Coverage report path | `backend/coverage.xml`, `backend/htmlcov/index.html` |
| Migration command | `alembic revision --autogenerate -m "..."` / `alembic upgrade head` |
| Env config syntax | `os.environ.get('VAR', 'fallback')` |

### Frontend

| Concern | Convention |
|---------|-----------|
| Test skip marker | .skip |
| Dev command | npm run dev |
| Test command | npx vitest run |
| Node config syntax | process.env.VAR \|\| 'fallback' |

### Browser Testing

See `.claude/guidelines/frontend-rules.md` ("Selenium Tests" section) for the 2-tier
DSL, `data-testid` conventions, and the ban on direct URL navigation.
