# Interview — Story 1: Auto-generate: доклад

## Scope

This is the first story in the core build sequence (see `stories.md`) and it's
deliberately narrow: **generation only, no editor UI**. In scope:

- User submits a generation request (тема / требования / объём / доп. пожелания) for
  document type "доклад" — the type is fixed for this story; эссе/сочинение/реферат are
  stories #2–#4.
- Request is enqueued (arq) and processed asynchronously by a worker that calls
  OpenRouter.
- User polls a status endpoint and, once done, reads the generated document (raw
  text/HTML) via a GET endpoint.

Out of scope (explicitly deferred to later stories):

- Rich-text editor (formatting, autosave, TipTap) — story #10.
- Saving user edits back to the document — story #10/#11 territory, not this story.
- Any `User`/auth concept — story #7. Story 1 is **fully anonymous** (see
  `.memory-bank/tasks/known-debt.md` #2).
- Model switching / tariffs — story #6/#8.

DECISION: a temporary, unauthenticated "list all generations" endpoint is in scope for
story 1 (no `user_id` filter — there isn't one yet). This is a deliberate stand-in for
"history," not the real history feature (#12), which will need a session/user identity
to scope the list per-user.

## External API/Service Documentation

- OpenRouter: https://openrouter.ai/docs — OpenAI-compatible chat completions API.
- Auth: Bearer token (`OPENROUTER_API_KEY`), sent as `Authorization: Bearer ...`.

## API Endpoints Used

| Endpoint | Status |
|----------|--------|
| OpenRouter `POST /api/v1/chat/completions` | NOT YET IMPLEMENTED |

DECISION: generation goes through **OpenRouter**, not the native Anthropic API — changed
during this interview from the earlier plan (see `.memory-bank/tech-details/backend.md`).
Rationale: OpenRouter is a single OpenAI-compatible gateway to Claude and other models,
so story #6's per-tariff model switching becomes a `model` string change instead of a
new vendor SDK/adapter. Client library: `openai` Python SDK, `base_url =
"https://openrouter.ai/api/v1"`.

## Token/Auth Requirements

- `OPENROUTER_API_KEY` — lives in `backend/.env`, read via plain env var (no cloud
  secret store yet, per existing decision).
- Specific model string for story 1 is **still open** — the user wants to pick it
  separately, not block the spec on it. Use a placeholder/config value
  (`OPENROUTER_MODEL` env var) so it can be swapped without a code change.

## Key Architectural Decisions

- DECISION: generation is asynchronous end-to-end. `POST /generations` enqueues an
  `arq` job and returns immediately with `{generation_id, status: "pending"}`; a
  separate worker process calls OpenRouter and updates the record.
- DECISION: generation status lifecycle — `pending` → `in_progress` → `completed` |
  `failed`. Client polls `GET /generations/{id}` for status + result.
- DECISION: OpenRouter call failure retry policy — the `arq` job retries a bounded
  number of times with backoff; after retries are exhausted, `generation.status =
  "failed"` and the client observes this via the status endpoint. No retry beyond that
  (no dead-letter queue, no manual replay UI — out of scope for story 1).
- DECISION: volume is specified in **pages** (a number field on the request), not word
  count or free text — translated into an approximate character/token budget for the
  prompt. Range: **1–10 pages**; outside that range is a 400 validation error (corrected
  2026-07-07 — this originally said 422, which contradicted `api-specs/generations_create.yaml`'s
  400/422 split: 400 is for missing/out-of-range/over-length fields, 422 is reserved for
  unsupported `document_type` or server-owned-field overrides. The API spec is the
  authoritative later-phase contract; caught during scenario 1.1's `/continue` work unit).
- DECISION: тема (topic) is required; требования and доп. пожелания (requirements,
  extra wishes) are optional fields.
- ACTION: pick the actual OpenRouter model string for story 1 in a follow-up (not
  blocking `/story` or `/test-spec` — it's a config value, not a scope change).

## Business Rules & Constraints

- `document_type` is fixed to `"доклад"` for this story (still modeled as a field on
  `Generation`, not hardcoded in the domain, since #2–#4 add the other types on the same
  entity shape).
- Validation: `topic` non-empty; `volume_pages` integer in `[1, 10]`; `requirements` and
  `extra_wishes` optional strings.
- No rate limiting / per-user quota in this story (quotas are tariff-based, story #8).

## Already Implemented (REUSE)

None — `backend/`, `acceptance/` are both empty. This is the first story.

## NOT Yet Implemented (Gaps)

Everything: domain (`Generation`, `Document`), usecases (`RequestGeneration`,
`GetGenerationStatus`, `ListGenerations`), REST adapter, DB adapter (SQLAlchemy models +
Alembic migration), scheduling adapter (arq worker + OpenRouter client), composition
root wiring.

## Cross-Story Dependencies

- Must ship before #2–#4 (эссе/сочинение/реферат) — they reuse the same `Generation`/
  `Document` shape, just a different `document_type` value.
- Must ship before #7 (Authorization) — #7 will need to retrofit `user_id` onto
  `Generation`/`Document` (tracked in `known-debt.md` #2).
- Must ship before #6 (Model switching) — #6 turns the OpenRouter `model` value from a
  fixed config into a per-tariff choice.
- Independent of #5 (Manual input mode), #8 (Billing) — no ordering constraint either way.

## Testing Considerations

- DECISION: acceptance tests use a **stub HTTP server standing in for OpenRouter**
  (the worker's OpenRouter client is pointed at the stub's `base_url` in the test
  environment) — never the real OpenRouter API. Rationale: real calls cost money and
  add network flakiness to every CI run. Manual/exploratory verification against the
  real OpenRouter API happens separately, outside the automated suite.
- Usecase tests: fake `JobQueue` and fake OpenRouter-client port (per `tdd.md`/`coding.md`
  conventions in the `python-fastapi-hex` profile) — no real Redis, no real HTTP.
- Scheduling adapter tests: real local Redis (from `infrastructure/.env`), `arq` in
  `burst=True` mode, against the OpenRouter stub — not the fake port used by usecase
  tests (see `templates/scheduling/test-class.md`).

## Performance/Rate Limits

- Generation must never be handled inline in the request (see `ExpectedLoad.md` —
  hundreds of concurrent users expected). Confirmed by the async/`arq` design above.
- `arq` job timeout: 300s default (from the tech profile's scheduling config) — a stuck
  OpenRouter call must not hang a worker slot forever.
- No specific concurrency/throughput target was set for story 1 beyond "must be async" —
  revisit once load-test stories are reached.
