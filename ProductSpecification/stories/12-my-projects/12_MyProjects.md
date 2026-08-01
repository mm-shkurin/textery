# Мои проекты (list / search / sort, grid + list view)

## Brief Description

One owner-scoped feed of the caller's work — saved `Document`s plus the `Generation`s that
never became one — searchable, sortable four ways, rendered as a grid or a list. Served by a
new `GET /api/v1/projects`; the existing `GET /documents` and `GET /generations` are marked
deprecated and keep working.

## Flow

1. User opens «Мои проекты». Client calls `GET /api/v1/projects?page=1&limit=20&sort=created_desc`.
2. Backend resolves the caller from the Bearer token and queries **both** sources in one SQL
   statement with `owner_id` as a predicate: all `Document`s, plus every `Generation` with no
   linked `Document`.
3. Backend applies search, sorts the merged set, and returns one offset page plus `total`.
4. Client renders the page. «Недавние проекты» is the first N items of the same response —
   not a second request.
5. User types in search → same endpoint with `q`; page resets to 1.
6. User picks a sort → same endpoint with `sort`; page resets to 1; `q` is preserved.
7. User toggles grid ⇄ list → client-side re-render of the same data, no request.
8. Clicking a document card opens it in the editor (`GET /documents/{id}`, story 5).
9. Clicking «Повторить» on a **failed** generation card calls
   `POST /api/v1/generations/{id}/retry` with an `Idempotency-Key`; the server copies the
   source row's parameters. No request body.
10. Empty result renders one of two distinct states: "no matches" or "no projects yet".

## Acceptance Criteria

Moved to `12_MyProjects_AcceptanceCriteria.md` — the folded hazard-scan guards made this
section longer than the whole rest of the spec.

## Validation Rules

| Field | Rule |
|-------|------|
| Authorization | Bearer access token required; account resolved server-side → 401 if missing/expired/non-access; fail closed if the check itself errors |
| page | exact decimal integer, 1..`PAGE_MAX`, default 1; else 400 `INVALID_PAGE` |
| limit | exact decimal integer, 1..100, default 20; else 400 `INVALID_LIMIT` |
| sort | one of `created_desc`\|`created_asc`\|`updated_desc`\|`title_asc`\|`type_asc`; else 400 `INVALID_SORT` |
| q | optional; trimmed; ≤200 Unicode code points → else 400 `INVALID_QUERY`; NFC-normalized; LIKE metacharacters escaped |
| preview | server-derived only, never accepted from the client; DB-side prefix read, code-point bounded, plain text |
| Idempotency-Key | required on `POST /generations/{id}/retry`; unique on `(owner_id, key)` in the database, not in process memory |

## Screen States

- **Grid view** / **List view** — same feed; the toggle is client-side only, no refetch, scroll
  position and active search preserved.
- **Recent projects** — first N of the same response; hidden under an active `q` or a non-default
  sort.
- **Search active, results** — filtered feed with a visible result count.
- **Search active, no matches** — action = clear the search.
- **No projects yet** — distinct empty state, action = create a project.
- **Failed generation card** — status + «Повторить»; retry-error variant with the button
  re-enabled.
- **Recovering generation card** — non-terminal past the stale threshold; labelled, no retry
  button (the sweep owns recovery).
- **Loading** — skeleton (absent from the mockups; design before frontend scenarios).
- **Error** — list failed to load, retry affordance that does not clear `q`/`sort`.

## Core Requirements

- New endpoint only. The two existing lists are not extended — a keyset anchor must be immutable,
  and `updated_at`/`title`/`type` all move. Reasoning in `interview.md`.
- Offset pagination is a deliberate trade: all four sorts and search with no cursor tricks, at the
  cost of linear deep-page scans. Revisit when one account's rows reach thousands.
- Offset paging over a **live** set can repeat or drop a row between two page requests. Accepted
  and stated in the contract; the client appends with dedupe on `(kind, id)`.
- The merge of the two tables is a **single SQL query** — sorting, `LIMIT/OFFSET`, and the
  `preview` prefix all run in the database. Stitching two queries in Python reads the caller's
  whole history per page.
- Search over `Document.content` uses `ILIKE '%…%'` with **no** full-text index — a conscious
  speed-vs-scope compromise, recorded in `.memory-bank/tasks/known-debt.md`; the replacement is
  `tsvector` + GIN with Russian morphology.
- The unindexed scan is bounded by **throughput**, not by a latency percentile — the project's
  declared Load Challenge Profile is Throughput (`ExpectedLoad.md`), and per-request p95 is
  explicitly out of scope for it. The load scenario asserts the feed sustains its rate with an
  error-rate ceiling while searches run, and that the per-account cap sheds the excess as 429
  rather than queueing it into the connection pool.
- No in-memory state: no cached feed, `total`, page window, or idempotency record. Multi-instance
  deployment; the database is the only shared state.
- Two new usecases — `ListProjects` over a new repository port, and `RetryGeneration`. Neither
  may call another usecase: `RetryGeneration` must not reach into `RequestGeneration`; shared
  construction goes to the domain.
- **A migration on `generations` is in scope**: an `idempotency_key` column plus
  `uq_generations_owner_idempotency_key`, mirroring `documents`. The table has neither today even
  though `generations_create.yaml` advertises the header as required — pre-existing drift that
  this story is the first to depend on. `POST /generations` starts honouring the header it
  already documents.
- Categories («Учебные / Деловые»), the `···` actions menu (story 11), and business document types
  are drawn but inert — no domain field, no endpoint, no behaviour in this story.
- Constants are pinned in `endpoints.md`: `PAGE_MAX` 1000, `preview` 200 code points, recent `N`
  4, debounce 300 ms, statement timeout 3 s, one in-flight search per account.
- OPEN (story 1, not closed here): a worker that fails every attempt is requeued by the sweep
  forever — `generations` has no attempt cap, so the row never reaches a terminal state. The feed
  labels it recovering; the real fix is a bounded attempt count, and the sweep is story 1's.
- OPEN (product): «Мои проекты» and the shipped «Мои работы» (`frontend/src/features/history/`)
  list the same rows. Whether the new page replaces that one is undecided; the deprecation of
  `GET /documents` implies it should.
- ACTION (design): icons for эссе and сочинение are missing from the kit — placeholder teal
  folders in the mockups.
