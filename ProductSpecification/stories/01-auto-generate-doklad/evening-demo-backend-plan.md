# Backend Working Plan — Evening Demo (2026-07-09)

Off-framework vertical slice (debt #10). Provider = GigaChat (debt #11), FakeProvider
until creds land. Generation runs in FastAPI `BackgroundTask`. Frontend polls GET @5s.
Build in order; one manual end-to-end verify at the end. Existing scaffolding is more
complete than progress.md claims — reuse it.

## Ordered steps (file-precise)

### 1. Domain — `backend/domain/src/generation/generation.py`
- Add `content: Optional[str]` to `__init__` (default None) and as a param.
- Add statuses: keep `PENDING_STATUS`; add `IN_PROGRESS`/`COMPLETED`/`FAILED` constants.
- Add methods:
  - `mark_in_progress()` → set status `in_progress`.
  - `complete(content: str)` → set `self.content`, status `completed`.
  - `fail(reason: str)` → status `failed` (store reason in content or a `failure_reason`;
    simplest: leave content None, status failed).
- `create(...)` unchanged (content starts None). Keep ≤200 lines — if tight, split later.

### 2. Domain model DB — `backend/adapters/db/src/model/generation/generation_model.py`
- Add `content: Mapped[Optional[str]] = mapped_column(String, nullable=True)`.
- Thread `content` through `from_domain` and `to_domain`.

### 3. Usecase port — `backend/usecase/src/adapters/generation_provider.py` (NEW)
- `class GenerationProvider(Protocol): async def generate(self, generation: Generation) -> str: ...`

### 4. Extend storage port — `backend/usecase/src/adapters/generation_storage.py`
- Add to Protocol: `async def get(self, generation_id: UUID) -> Optional[Generation]: ...`
  and `async def update(self, generation: Generation) -> None: ...`.

### 5. DB adapter — `backend/adapters/db/src/access/generation/generation_storage.py`
- Implement `save`: `self._session.add(GenerationModel.from_domain(g)); await commit`.
- Implement `get(id)`: `session.get(GenerationModel, id)` → `.to_domain()` or None.
- Implement `update(g)`: merge/load model, copy fields, commit. Keep it simple (get →
  mutate columns → commit), no fancy dirty-tracking.

### 6. Alembic migration — `generations` table (+ `content`)
- `alembic revision --autogenerate -m "generations table with content"` then check the
  generated file. If Alembic env isn't wired yet, create table via migration by hand:
  columns per GenerationModel incl. `content` nullable, status CHECK constraint.
- `alembic upgrade head` against the dev DB (`DATABASE_URL`).

### 7. Provider adapter — `backend/adapters/<provider>/`
- `FakeProvider.generate()` → returns fixed multi-paragraph Russian doklad text now
  (unblocks the whole slice without creds).
- `GigaChatProvider` (swap in when creds ready): OAuth2 token from
  `ngw.devices.sberbank.ru` (Basic client creds + scope `GIGACHAT_API_PERS`), then
  POST chat/completions to `gigachat.devices.sberbank.ru`. Handle the Russian-CA TLS
  cert properly. Prompt built from `generation.topic` + `generation.volume_pages`.
  Creds from env (`GIGACHAT_CREDENTIALS` / client id+secret).

### 8. Usecase `GenerateDocument` — `backend/usecase/src/generation/generate_document.py` (NEW)
- Ctor: `storage: GenerationStorage, provider: GenerationProvider`.
- `async execute(generation_id)`: load via storage.get; `mark_in_progress()` + update;
  `content = await provider.generate(g)`; `g.complete(content)`; update. On provider
  exception → `g.fail(str(e))` + update (never leave stuck). No calls into other usecases.

### 9. Usecase `GetGeneration` — `backend/usecase/src/generation/get_generation.py` (NEW)
- Ctor: `storage`. `async execute(id) -> Optional[Generation]` → storage.get.

### 10. Composition root — `backend/application/src/app/container.py` (NEW)
- Build engine + session factory (`session.py`), storage, provider (Fake/GigaChat by
  env), and factory functions returning `RequestGeneration` / `GenerateDocument` /
  `GetGeneration` with real deps. This replaces `RequestGeneration()` no-arg default.

### 11. REST POST fix — `backend/adapters/rest/src/router/generation/generation_router.py`
- `get_generation_usecase()` → resolve `RequestGeneration` from container (real deps).
- Endpoint: after `usecase.execute(...)` returns the `Generation`, schedule
  `background_tasks.add_task(run_generate_document, generation.id)` (FastAPI
  `BackgroundTasks` param), and return body
  `{"generation_id": str(g.id), "status": g.status, "created_at": g.created_at.isoformat()}`
  with 201. `run_generate_document` builds a fresh session-scoped `GenerateDocument`
  from the container and calls execute.

### 12. REST GET — `generation_router.py` (or a new response DTO file if >200 lines)
- `@router.get("/{generation_id}")` → `GetGeneration.execute(id)`; 404 if None; else body
  `{generation_id, status, created_at, topic, volume_pages, document_type, content}`.
  `content` is null until completed.

### 13. Manual end-to-end verify
- Start DB (dev compose), `alembic upgrade head`, run backend
  (`uvicorn app.main:app --reload --port $BACKEND_PORT`).
- `POST /api/v1/generations` (Idempotency-Key header, body `{document_type:"doklad",
  topic:"...", volume_pages:5}`) → 201 with id + status pending.
- Poll `GET /api/v1/generations/{id}` → within seconds `status: completed`, `content`
  populated (FakeProvider text).
- Confirm a provider error path → `status: failed`, not stuck.

## File-size guard
After each new/edited file: `wc -l` ≤ 200. Split router into POST/GET files or extract a
response-DTO module if it crosses the limit.

## Not in this slice (deferred — debt #10)
arq worker, retry/reconciliation, idempotency persistence, not-found edge coverage beyond
GET 404, per-scenario TDD tests, real GigaChat creds if started on Fake.
