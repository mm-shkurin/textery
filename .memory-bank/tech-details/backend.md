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

- **Generation engine:** external LLM API (Anthropic Claude) — real generation calls,
  not templates or a local model. Product is literally branded "Textery AI".
- **Concurrency model:** hundreds of concurrent users expected (see
  `ProductSpecification/ExpectedLoad.md`) → text generation must be async/queued
  (background task + status polling or similar), never a request held open for the
  duration of an LLM call.
- **Auth:** email+password with a mocked email verification code (no real mail
  integration) + Yandex ID OAuth + VK ID OAuth. **No Google** anywhere in this project —
  the reference architecture doc's Google OAuth suggestion does not apply here.
- **Subscriptions:** 3 tariffs, differing by AI model tier and monthly generation quota.
  Billing fully mocked (no real payment provider).
- **Document export:** Word + PDF generation from the editor's content — explicitly
  lower priority than the rest of the flow.

## Open — must resolve before the `python-fastapi-hex` tech profile can be authored
- ORM / persistence: SQLAlchemy vs raw asyncpg vs other?
- Migrations tool: Alembic vs other?
- DI approach: FastAPI's built-in `Depends()` vs a dedicated container
  (e.g. `dependency-injector`)?
- Test runner / mocking: pytest + what mocking library (unittest.mock, pytest-mock)?
- Coverage tool: coverage.py / pytest-cov?
- Async task queue for generation: Celery / arq / FastAPI `BackgroundTasks` (too weak for
  this scale) / other?
- Docx/PDF generation library (python-docx + a PDF renderer, or a different approach)?

Once these are answered, `.claude/tech/python-fastapi-hex/` (coding.md, tdd.md,
infrastructure.md, templates/) gets written, and
`ProductSpecification/technology.md`'s Backend section gets filled in from it — see
that file's current TODO markers.

## Entities / domain model
Draft entities from the reference architecture doc (`.memory-bank/комплект продуктовой
архитектуры.txt`): User, MarketingProfile, Subscription, Generation, Document,
AnalyticsEvent. Not yet formalized as domain code — no story has gone through
`/interview` → `/story` yet (`ProductSpecification/stories.md` now has a 12-story
backlog, none started).
