# Evening Demo Plan — Auto-generate: доклад (2026-07-09)

Goal: working end-to-end doklad generation, backend + frontend, by tonight.
Sprint velocity through the full TDD framework is too slow for the deadline. This slice
is built **directly against the hexagonal architecture, off the TDD framework** — no
red/green/adapters-discovery/test-review/coverage/refactor/agent-review/premortem per
scenario. Verify by one manual end-to-end run + browser. Tech-debt of this deviation:
`.memory-bank/tasks/known-debt.md` #10 (framework skip) and #11 (GigaChat provider).

## Decisions (2026-07-09)
- **Off-framework** for this slice — hand-build by layer, one manual verify. (debt #10)
- **Provider = GigaChat (Sber), own creds** — not OpenRouter. Adapter `GigaChatProvider`.
  OAuth2 token flow + Russian-CA TLS quirk, `gigachat` SDK or raw REST. (debt #11)
- If GigaChat creds not ready at build time → start on `FakeProvider` (fixed doklad
  text), swap in `GigaChatProvider` once creds land.
- **Generation runs in a FastAPI `BackgroundTask`** (not arq for the demo). arq worker
  deferred — revisit post-demo (see debt #6 for the arq-vs-alternatives history).
- **Frontend polls `GET /generations/{id}` every 5s** until `completed`/`failed`.

## Real state before this slice (code, not checkboxes)
Backend works: domain validation (topic/volume), usecase persist+enqueue logic (ports
stubbed), REST POST 400 errors. Missing: REST POST happy-path (router calls
`RequestGeneration()` with no args, no response body), DB `save` (NotImplementedError),
provider port (does not exist), worker, `GET` endpoint, `container.py`.
Frontend works: Landing, TypeModal, ModeModal. Missing: chat/form (placeholder), API
client, submit + poll + display.

## Backend plan (do first — frontend needs a real GET)
1. **Domain** `Generation`: add `content` field, `complete(content)` and `fail(reason)`
   methods, statuses `completed` / `failed` (alongside existing `pending`).
2. **Usecase port** `GenerationProvider` — `async generate(generation) -> str`.
3. **Provider adapter** `GigaChatProvider` (openai-incompatible: GigaChat OAuth2 +
   endpoint, creds from env, TLS-cert handled). Builds the prompt from `topic` + `volume`.
   `FakeProvider` fallback while creds absent.
4. **DB**: implement `save`, `get(id)`, `update`; Alembic migration for `generations`
   (+ `content` column).
5. **Usecase** `GenerateDocument` — calls provider, writes result via storage.update
   (invoked from the BackgroundTask; on provider error → `generation.fail(...)`).
6. **Usecase** `GetGeneration` — returns status + content for an id.
7. **REST POST fix**: `container.py` wires the real adapters into the usecases; response
   body returns `generation_id` / `status` / `created_at`; schedules the BackgroundTask.
8. **REST** `GET /api/v1/generations/{id}` → status + content.
9. Manual run: POST → poll GET (5s) → `completed` with generated text. (Optionally one
   acceptance test as demo proof.)

## Frontend plan
1. **API client**: `createGeneration(topic)` (POST), `getGeneration(id)` (GET).
2. **Hook** `useGeneration` — submit, poll GET every **5s**, states
   `pending` / `completed` / `failed`.
3. **Chat workspace** component (mockups 05-07, doc-left / chat-right): topic chat input
   → send → loading indicator ("ИИ пишет…", debt #5) → document display on completed.
4. Replace App `form` placeholder with a `chat` step wired to the hook.
5. Manual browser check end-to-end against the running backend.

## Deferred (backfill post-demo)
Per-scenario TDD coverage for the whole slice (debt #10); arq worker (using BackgroundTask
now); real GigaChat creds if started on FakeProvider (debt #11); retry / reconciliation;
idempotency persistence; not-found / edge / failure states beyond happy-path + basic fail;
`technology.md` update to GigaChat (debt #11).
