# Auto-generate: доклад

## Brief Description

Anonymous user submits a "доклад" generation request (topic, volume, optional
requirements/wishes); the system generates it asynchronously via OpenRouter and the
user retrieves the resulting document once ready.

## Flow

1. User opens the generation form for document type "доклад".
2. User enters topic (required), volume in pages 1-10 (required), requirements
   (optional), extra wishes (optional).
3. User submits the request.
4. System creates a `Generation` record (status `pending`), enqueues an `arq` job, and
   returns `generation_id` immediately — no blocking on the LLM call.
5. Worker picks up the job, sets status `in_progress`, calls OpenRouter with a prompt
   built from the request fields.
6. On success: worker creates a `Document` with the generated content, sets `Generation`
   status to `completed`.
7. On failure after bounded retries: `Generation` status set to `failed`.
8. Client polls `GET /generations/{id}` for status.
9. Once `completed`, client reads the document content from the same response.
10. Client can list all generations via a temporary, unscoped `GET /generations`.

## Acceptance Criteria

- `POST /generations` returns 201 with `generation_id` and `status=pending` without
  waiting on the LLM call.
- `GET /generations/{id}` returns current status and, once `completed`, the document
  content.
- A request with `document_type=доклад`, valid topic, and volume 1-10 completes
  end-to-end (worker calls a stub OpenRouter server in tests, the real one in prod).
- Requests with missing topic or out-of-range volume are rejected with 400 before
  anything is enqueued (400 = field-level validation error; 422 is reserved for
  unsupported `document_type` or server-owned-field overrides — see Validation Rules
  below and `api-specs/generations_create.yaml`. Corrected 2026-07-07, matching the same
  fix already made in `interview.md` — this line was missed the first time).
- OpenRouter failures retry a bounded number of times, then the generation moves to
  `failed` — never stuck in `pending`/`in_progress` forever.
- `GET /generations` returns all generations, regardless of origin (no auth binding yet).

## Validation Rules

| Field | Rule |
|-------|------|
| topic | required, non-empty string |
| volume_pages | required, integer, 1–10 |
| requirements | optional string, max 2000 chars |
| extra_wishes | optional string, max 2000 chars |
| document_type | fixed to `"доклад"`; any other value is rejected (422), never silently defaulted |

## Screen States

Revised 2026-07-07 — entry flow now goes through Landing/modals, not a standalone form
page. API contract is unaffected (still `POST /generations` + poll); this only changes
what the frontend shows. See `.memory-bank/tasks/known-debt.md` #5 for the streaming
simplification.

- **Landing** (minimal slice pulled forward from story #9 — hero + "Попробовать
  бесплатно" CTA only, not the full marketing page). Reference: `.memory-bank/Landing.png`.
- **Modal — document type select**: доклад / эссе / сочинение / реферат. Only доклад is
  active this story; the other three show a "скоро" badge (same pattern as the existing
  `mockups/desktop/01-generation-form.html`, just relocated into a modal). Reference:
  `.memory-bank/Тип документа.png`.
- **Modal — mode select**: Ручной режим / Автоматический режим. Only Автоматический is
  active; Ручной shows "скоро" (story #5 isn't built yet — same disabled-option
  convention as the type modal). Reference: `.memory-bank/Тип Работы.png`.
- **Generation form** (topic / volume / requirements / wishes, submit) — reached after
  both modals; this is the existing `01-generation-form.html` mockup, now a step inside
  the flow rather than the entry point.
- **"Chat" progress screen**: pending/in-progress shown as a simple loading indicator
  (e.g. "ИИ пишет...") — NOT real token streaming yet (known-debt #5). Reference:
  `.memory-bank/Автоматическая работа.png` for the intended look (chat-style panel next
  to the document being written), not its literal content.
- **Completed state**: generated document content shown in that same chat/result screen.
- **Failed state**: error message, same screen.

Mockups regenerated 2026-07-07 to match this flow: `01-landing`, `02-type-modal`,
`03-mode-modal`, `04-generation-form` (revised — type selector removed, now shown as a
breadcrumb chip since it's chosen in an earlier modal), `05-chat-pending`,
`06-chat-completed`, `07-chat-failed` (desktop + mobile, 14 files total).

## Core Requirements

- Generation processing is asynchronous (`arq` background job) — never inline in the
  request/response cycle.
- No `User`/auth concept anywhere in this story's domain model (fully anonymous).
- OpenRouter integration via the `openai` SDK; `OPENROUTER_API_KEY` + `OPENROUTER_MODEL`
  env config, both **validated at startup** (fail fast on boot if missing, not lazily on
  first job); the test-vs-prod `base_url` is an explicit, validated config source, never
  convention.
- Bounded retry with backoff on OpenRouter failures before marking `failed`; failure
  handling is **differentiated**: 4xx fails fast without burning the retry budget,
  5xx/timeout/malformed-empty-body retries per policy.
- Retry backoff includes **randomized jitter**, not just a fixed/exponential delay.
- Acceptance tests exercise a stub OpenRouter server — never the real API.
- `Generation.id` (`generation_id`) is a **non-sequential opaque identifier** (UUID), not
  a guessable sequential integer — defense-in-depth ahead of story #7's real
  authorization.
- `POST /generations` requires a client-supplied idempotency key; **posting the same key
  twice returns the existing `generation_id`** (no re-create, no re-enqueue) — this is a
  tested acceptance criterion, not just a stated requirement.
- `Generation` status transitions (`pending → in_progress → completed|failed`) are
  **atomic conditional updates** gated on the expected prior status (compare-and-swap /
  worker lease) — a single guard that closes: duplicate `arq` job redelivery processing
  the same generation twice, two worker instances racing the same row, and any write
  landing on an already-terminal (`completed`/`failed`) row.
- `Document` insert + `Generation` status update commit **atomically** (no orphan
  document against a stale status, no orphan status with no document); the OpenRouter
  call itself happens **outside** any open DB transaction.
- The `arq` job deadline is sized with margin over (per-call timeout × retries +
  backoff); an in-flight OpenRouter call is **cancelled**, not left running, when the
  deadline fires; a **hung** (non-erroring) call also resolves to `failed`, not just an
  erroring one.
- A `Generation` left in `pending`/`in_progress` past a defined staleness window (worker
  died mid-job, no heartbeat) is swept to `failed` by a reconciliation mechanism —
  distinct from, and in addition to, the retry-exhaustion guard above.
- `POST /generations`'s request DTO binds **only** the 4 documented fields; a body
  containing a server-owned field (`status`, `id`, or a `document_type` override) is
  rejected, not silently ignored.
- Document content and any echoed user input (`topic`/`requirements`/`extra_wishes`) are
  served as **escaped text**, never rendered as raw unescaped HTML.
- Failed generations persist/log a **distinguishable failure category**
  (rate_limit/content_policy/timeout/malformed-response/etc.) server-side, even though
  the client-facing `status` field stays a bare `failed`.
- `OPENROUTER_API_KEY` and raw OpenRouter error bodies **never** appear in an HTTP
  response or captured log (redaction, tested with a sentinel value).
- `GET /generations` is **paginated with a stable keyset** (`id`/`created_at` + unique
  tiebreaker), never offset/limit — the table grows continuously and unscoped.
- The `volume_pages` → LLM token/character budget conversion is an explicit, **pinned
  constant** with boundary tests at 1 and 10 pages using Cyrillic-heavy fixture text (not
  ASCII) — no single ratio calibrated on Latin text is assumed to hold for "доклад".
- `arq` worker runs with a configured `max_jobs` concurrency ceiling (a floor exists now;
  the exact number is tuned during the load-test scenarios, not this story).
