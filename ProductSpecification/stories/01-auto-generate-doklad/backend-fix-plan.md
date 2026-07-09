# Backend Fix Plan — arch violation + hardcode + red tests (2026-07-09)

Evening-demo slice is code-complete and boots, but `pytest backend/` is RED and the REST
adapter violates the dependency rule. Fix these before the demo. Order matters: fix the
architecture (1) first — it also un-reds the test.

## Problem 1 — REST adapter imports the application layer (dependency-rule violation)
`backend/adapters/rest/src/router/generation/generation_router.py` does
`from container import create_generate_document, create_get_generation,
create_request_generation`. `container.py` lives in the **application** layer. Flow is
strictly inward `application → adapters → usecase → domain`; an adapter importing
application is forbidden (coding-rules.md). This is also why the rest test can't collect
(`ModuleNotFoundError: No module named 'container'` — container isn't on the rest test's
sys.path).

**Fix — invert the wiring via FastAPI dependency overrides:**
1. In `generation_router.py`, delete the `container` import. Define three dependency
   stubs the router owns, meant to be overridden by the composition root:
   ```python
   def get_request_generation_usecase() -> RequestGeneration:
       raise NotImplementedError("wired by the application composition root")
   def get_get_generation_usecase() -> GetGeneration:
       raise NotImplementedError("wired by the application composition root")
   def get_generate_document_usecase() -> GenerateDocument:
       raise NotImplementedError("wired by the application composition root")
   ```
2. The POST endpoint takes `generate_document: GenerateDocument =
   Depends(get_generate_document_usecase)` and schedules
   `background_tasks.add_task(generate_document.execute, generation.id)` — no `container`
   import, no local `run_generate_document` that reaches into application.
3. In `backend/application/src/app/main.py` (application layer — allowed to import
   everything), after `app.include_router(...)`, wire the overrides:
   ```python
   from app.container import (create_request_generation, create_get_generation,
                              create_generate_document)
   from router.generation.generation_router import (
       get_request_generation_usecase, get_get_generation_usecase,
       get_generate_document_usecase)
   app.dependency_overrides[get_request_generation_usecase] = create_request_generation
   app.dependency_overrides[get_get_generation_usecase] = create_get_generation
   app.dependency_overrides[get_generate_document_usecase] = create_generate_document
   ```
   Add `_APPLICATION_SRC` to sys.path in main.py if `app.container` isn't importable yet.

## Problem 2 — stale symbol in the rest test
`backend/adapters/rest/tests/router/generation/test_generation_router.py:5` imports
`get_generation_usecase`, which no longer exists (renamed to
`get_request_generation_usecase`). Update the import and the
`app.dependency_overrides[...]` key in the test to `get_request_generation_usecase`.
After problems 1+2, `pytest backend/` must be GREEN — run it and confirm.

## Problem 3 — `fail(reason)` drops the reason (silent data loss)
`backend/domain/src/generation/generation.py` `fail()` sets status `failed` but discards
`reason`; `content` stays None, so a failed generation carries no error detail. Store it:
persist the reason (simplest: `self.content = reason` on fail, or add a
`failure_reason` field threaded through the model + migration + `GenerationDetailDto`).
Pick the field approach only if there's time; otherwise `content = reason` is acceptable
for the demo — but make failed rows carry *something*.

## Problem 4 — hardcode / lifecycle in the composition root
`backend/application/src/app/container.py`:
- **Session leak:** every factory calls `_session_factory()` and never closes the
  session — each POST/GET/background task leaks a connection. Give each usecase a
  session that is closed after use (dependency that yields then closes, or close in a
  `finally`). For the background task the session must outlive the request but still be
  closed when `execute` finishes.
- **`NoOpGenerationQueue`** silently drops `enqueue` (generation runs via BackgroundTask
  instead). Acceptable for the demo, but add a comment saying so and reference
  known-debt (arq worker deferred) so it isn't mistaken for a bug.
- **Provider default** `os.environ.get(GENERATION_PROVIDER_ENV_VAR, "gigachat")` — keep
  env-driven, but since GigaChat creds aren't in the environment yet, the running
  demo config must set `GENERATION_PROVIDER=fake` (document in `.env`/compose) or the
  first real POST will fail at token fetch. Confirm which provider the demo runs on.
- **Module-level `create_engine()`** reads `DATABASE_URL` at import time and crashes the
  whole app import if it's unset. Fine for the running app (env present), but keep in
  mind for any test that imports `container`.

## Verify (end-to-end, once problems 1-4 done)
1. Postgres up, `DATABASE_URL` set, `alembic upgrade head`
   (migration `c8ed82e70d3e_generations_table_with_content`).
2. `GENERATION_PROVIDER=fake`, run `uvicorn app.main:app --port $BACKEND_PORT`.
3. `POST /api/v1/generations` (Idempotency-Key, `{document_type, topic, volume_pages:5}`)
   → 201 with `generation_id`/`status: pending`.
4. Poll `GET /api/v1/generations/{id}` → `completed` within seconds, `content` = fake
   doklad text.
5. Force a provider error (temporarily point provider at a bad URL / raise) → confirm
   `status: failed` with a non-null reason, never stuck in `in_progress`.
6. `pytest backend/` GREEN.

## Out of scope (still deferred — known-debt #10/#11)
arq worker, per-scenario TDD backfill, real GigaChat creds, retry/reconciliation,
idempotency persistence.
