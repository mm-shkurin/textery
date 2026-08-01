# Мои проекты — API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/projects | The caller's feed: documents + generations no document was made from. Search, 4 sorts, offset pages. |
| POST | /api/v1/generations/{id}/retry | «Повторить» on a failed generation — reruns it from its stored parameters. |

Contracts: `api-specs/projects_list.yaml`, `api-specs/generations_retry.yaml`.
`documents_list.yaml` and `generations_list.yaml` gained `deprecated: true` and a note
pointing here; neither changed behaviour.

## Decisions this step had to make

**«Повторить» is its own endpoint, not a re-`POST /generations`.** The story spec said
the client re-sends "the same parameters" *and* that retrying another account's
generation must be denied — and those cannot both hold: `POST /api/v1/generations` takes
parameters and no id, so the server has nothing to authorize. Naming the source by id
fixes both halves at once. There is no request body, so the mass-assignment surface is
gone rather than allowlisted, and the parameters come from the row instead of the
browser. Cost: a second usecase (`RetryGeneration`), where the story spec promised one.
It must not call `RequestGeneration` — shared construction belongs in the domain.

**Retry is allowed only from `failed`.** `pending`/`in_progress` → 409. The reason is in
the code that already exists: `RequeueStaleGenerations` sweeps rows stuck past
`GENERATION_STALE_AFTER_MINUTES` (default 10) back to pending and re-triggers them. A row
the user sees as "stuck" is therefore usually still alive, and a retry button on it runs
the same generation twice — two documents, two model bills, one piece of work. So the
feed marks such rows `retryable: false`; recovery is the sweep's job, not the user's.

**Idempotency is `(owner_id, Idempotency-Key)`, in the database.** Keying on the header
alone is the literal reading of the story spec and is a cross-account disclosure: the
replay path short-circuits before any ownership logic, so a colliding key returns another
account's generation. This mirrors `uq_documents_owner_idempotency_key`, which already
exists on `documents`.

**This forces a migration on `generations`.** The table has no `idempotency_key` column
and no unique constraint today, even though `generations_create.yaml` documents the
header as required — a pre-existing contract/code drift that story 12 is the first to
actually depend on. So the story ships: a column + `uq_generations_owner_idempotency_key`,
and `POST /generations` starts honouring the header it already advertises. This
contradicts the story spec's "no migration is strictly required"; the spec was written
before this endpoint existed and has been corrected.

**The old failed card stays** after a retry (the deferred ACTION). Nothing is deleted or
mutated, the new generation is a separate row, and the feed shows both — which is what
"the user never watches a row vanish" already asked for. Replacing it would have made
this a destructive operation and re-fired a hazard group.

**`kind` is the source table, never a status.** The story spec had an unknown generation
status fail closed to `kind: "unknown"`, which would flip a row's identity — and `(kind,
id)` is the item key and the sort tiebreak. The fail-closed value moved to `status`.

**Per-kind sort mapping**, which the spec left implicit: both tables carry `created_at`,
`updated_at` and a NOT NULL `document_type`, so only `title_asc` needs a mapping —
`documents.title`, `generations.topic`, blanks last. `updated_at` on `generations` is
storage-owned and already exists (the sweep needs it).

## Constants pinned here

| Constant | Value | Why |
|----------|-------|-----|
| `PAGE_MAX` | 1000 | With `limit` 100 that caps `OFFSET` at 100 000 — bounds both the arithmetic and the deep-scan lever. |
| `preview` length | 200 code points | Enough for a first line; read as a SQL prefix so page bytes don't scale with document size. |
| Recent-projects `N` | 4 | The grid mockup shows four. |
| Search debounce | 300 ms | UI affordance only — the real bound is the per-account cap below. |
| Statement timeout | 3 s | Below the gateway read timeout, so a client is never told 504 while the scan runs on. |
| Search concurrency | 1 in-flight searching request per account (else 429 `SEARCH_BUSY`) | The content scan is unindexed; a browser debounce does nothing for a second tab or a scripted client. |
| Response-time bound | p95 < 800 ms for a worst-case `q` against a seeded 500-row account | The load scenario asserts this. A recorded baseline was the earlier wording and nothing could go red on it. |

## Known gap, not closed here

A generation that fails inside the worker every time is requeued by the sweep forever —
there is no attempt cap on `generations`, so it never reaches a terminal state and the
feed shows it as running indefinitely. The feed's honest move is to label a non-terminal
row older than the stale threshold as recovering rather than running; the actual fix (a
bounded attempt count and a terminal `failed`) belongs to story 1, which owns the sweep.
