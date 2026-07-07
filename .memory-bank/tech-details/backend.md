# Tech Details — Backend

## Status
No code written yet — `backend/` is still empty. Story 1's spec pipeline is complete
(`/interview` → `/story` → `/mockups` → `/api-spec` → `/test-spec`, hazard-catalogue
scanned twice — see `ProductSpecification/stories/01-auto-generate-doklad/` and
`.memory-bank/tasks/sprint-plan.md`'s progress log for the full breakdown). All items
below are now confirmed, not proposed. Next step is the actual red/green TDD loop.

## Decided
- **Language/framework:** Python + FastAPI.
- **Architecture:** Hexagonal (Ports & Adapters), mapped onto continue-framework's Clean
  Architecture layers: `domain` (zero framework deps) ← `usecase` (defines ports) ←
  `adapters` (REST/DB/email/... implement the ports) ← `application` (composition root).
- **Methodology:** strict TDD/ATDD via `/continue` — see
  [steerings/development-conventions.md](../steerings/development-conventions.md).

- **Generation engine:** external LLM API via **OpenRouter** (OpenAI-compatible gateway,
  `openai` Python SDK pointed at `https://openrouter.ai/api/v1`, secret `OPENROUTER_API_KEY`)
  — corrected 2026-07-06 during story 1's `/interview` from the earlier plan to call the
  Anthropic API directly. Chosen because it gives access to Claude and other models
  through one client, which makes story 6's per-tariff model switching a `model` string
  change instead of a new vendor SDK/adapter. Real generation calls, not templates or a
  local model — product is literally branded "Textery AI"; specific model for story 1 is
  still open (see story 1's `interview.md`).
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
- **Task queue:** `arq` (Redis-backed, async-native — fits FastAPI/asyncio without
  Celery's sync-worker/eventlet baggage). Generation is never handled inline in the
  request.
- **Prompt design:** one template, parameterized by document type (доклад/эссе/
  сочинение/реферат select params, not four separate prompts).
- **Database:** PostgreSQL. **Migrations:** Alembic. **ORM:** SQLAlchemy 2.0 (async
  engine) — confirmed 2026-07-06. Alembic autogenerate diffs against SQLAlchemy metadata.
- **DB adapter module name:** `backend/adapters/db` (not `h2` — CLAUDE.md's architecture
  table had a leftover `h2` placeholder from the framework's default Java/H2 template;
  corrected 2026-07-06 to match the real Postgres/SQLAlchemy stack and the reference
  profiles' convention).
- **DI:** FastAPI's built-in `Depends()` + a manual composition root (a small
  `container.py`/`bootstrap.py` wiring adapters to usecase ports at app startup) — no
  separate DI framework (`dependency-injector` etc.) — confirmed 2026-07-06. Simplest
  option that still respects Hexagonal boundaries.
- **Test runner / mocking / coverage:** `pytest` + `pytest-mock` (thin wrapper over
  `unittest.mock`, matches pytest fixture style) + `pytest-cov` (wraps `coverage.py`) —
  confirmed 2026-07-06. `pytest-asyncio` also required (async engine + async usecases
  mean most tests are `async def` — mechanical consequence of the SQLAlchemy async
  choice, not a separate decision).
- **Secrets:** no cloud provider chosen yet (see `infra/.memory-bank/index.md`) — Anthropic
  API key lives in a local `.env` for now, read via plain env var. Revisit once a cloud
  is picked; don't build cloud-secret wiring (Lockbox or otherwise) before that.

## Decided — build-order architecture (2026-07-06, driven by ProductSpecification/stories.md core sequence)
Story 1 (auto-generate доклад) ships **before** story 7 (authorization). Generation is
**fully anonymous until story 7** — no `User` concept, no `userId` field on `Generation`/
`Document` in the initial domain model. When story 7 lands, this needs an explicit
migration/rework to attach ownership — accepted as a deliberate later-story cost in
exchange for not guessing the User shape now. Flag this tradeoff in story 7's interview
and design-preview.

## Open
- Docx/PDF generation library (python-docx + a PDF renderer, or a different approach) —
  low priority, needed around story 5 at the earliest.

All blocking items resolved 2026-07-06. `.claude/tech/python-fastapi-hex/` (coding.md,
tdd.md, infrastructure.md, templates/) is authored, and
`ProductSpecification/technology.md`'s Backend section is filled in from it.

## Entities / domain model
Draft entities from the reference architecture doc (`.memory-bank/комплект продуктовой
архитектуры.txt`): User, MarketingProfile, Subscription, Generation, Document,
AnalyticsEvent — but per the build-order decision above, `User`/`MarketingProfile` don't
enter the domain until story 7; stories 1–4 only need `Generation` + `Document`. Not yet
formalized as domain code — no story has gone through `/interview` → `/story` yet.
`ProductSpecification/stories.md` now has the 8-story core sequence + a secondary
backlog layered on top later.
