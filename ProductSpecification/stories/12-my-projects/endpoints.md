# Мои проекты — API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/projects | The caller's feed: documents + generations no document was made from. Search, 4 sorts, offset pages. |
| POST | /api/v1/generations/{id}/retry | «Повторить» on a failed generation — reruns it from its stored parameters. |

Contracts: `api-specs/projects_list.yaml`, `api-specs/generations_retry.yaml`.
`documents_list.yaml` and `generations_list.yaml` gained `deprecated: true` and a note
pointing here; neither changed behaviour.

**Two endpoints, not three.** No separate "recent projects" call — that section is the
first four items of the same page. A second request for a slice of data already in hand is
the kind of endpoint the MVP rule exists to refuse.

**`preview` is a new field, `total` is a new concept.** The keyset endpoints deliberately
omit `total` (counting per page is the scan a cursor avoids); offset paging needs it, and
it therefore shares the search path's statement timeout and cancellation rather than being
a second unbounded count.

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

**This forces a migration on `generations`** — and unlike the `documents` one it
"mirrors", this table is not empty and is written continuously by the sweep, so the shape
matters:

- `idempotency_key` is **nullable**. NOT NULL would abort the deploy on every existing
  row; a backfilled `''` would collide on the first account with two generations. Legacy
  rows keep NULL, and Postgres treats NULLs as distinct, so they neither collide nor are
  constrained. New rows always carry a key because the endpoints require the header.
- `source_generation_id`, nullable, self-referencing — without lineage the replay path
  cannot tell a repeat of *this* retry from the same key used against a different source,
  and the 409 in `generations_retry.yaml` would be unwritable.
- The unique index is built `CONCURRENTLY`, under a `lock_timeout`. A plain build takes
  `ACCESS EXCLUSIVE` over the whole table while every replica's sweep is issuing
  `UPDATE`s against it — the `documents` precedent was a `create_table` on zero rows and
  says nothing about this case.

`POST /generations` also starts honouring the header it already advertises: a replayed key
returns the existing generation (200) instead of creating a second. That is a behaviour
change to a story-1 endpoint, so it carries its own acceptance scenarios rather than
riding along.

This contradicts the story spec's "no migration is strictly required"; the spec was
written before this endpoint existed and has been corrected.

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
| Statement timeout | 3 s, `SET LOCAL` | Below the gateway read timeout, so a client is never told 504 while the scan runs on. `SET LOCAL` because a bare `SET` on a pooled connection outlives the request: the next borrower inherits 3 s, and the first query to start failing would be the sweep's contended `UPDATE`. |
| Search concurrency | 1 in-flight searching request per account (else 429 `SEARCH_BUSY`), slot in the database with a 10 s TTL | The content scan is unindexed; a browser debounce does nothing for a second tab or a scripted client, and an in-process counter bounds nothing across replicas. The TTL exists because a pod killed mid-scan would otherwise hold the account's only slot forever. |
| Retry ceiling | 5 per source generation (else 429 `RETRY_LIMIT_REACHED`) | The fresh-key rule that keeps the button alive after a second failure also means idempotency bounds nothing. Every unpaid path here has a cap; this is the one that spends money. |
| Load bound | sustained rate with an error-rate ceiling, not p95 | `ExpectedLoad.md` declares a **Throughput** profile and puts per-request latency percentiles out of scope. The scan's cost is bounded by the statement timeout and shed by the concurrency cap; the load scenario asserts rate and error rate. |

## Known gap, not closed here

A generation that fails inside the worker every time is requeued by the sweep forever —
there is no attempt cap on `generations`, so it never reaches a terminal state and the
feed shows it as running indefinitely. The feed's honest move is to label a non-terminal
row older than the stale threshold as recovering rather than running; the actual fix (a
bounded attempt count and a terminal `failed`) belongs to story 1, which owns the sweep.
