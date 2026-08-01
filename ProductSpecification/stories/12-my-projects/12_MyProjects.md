# Мои проекты (list / search / sort, grid + list view)

## Brief Description

One owner-scoped feed of the user's work — documents plus generations that never became
documents (failed/unfinished) — with search, four sort criteria, and a grid/list view toggle,
served by a new `GET /api/v1/projects`.

## Flow

1. User opens «Мои проекты».
2. Client calls `GET /api/v1/projects?page&limit&sort&q` (Bearer required).
3. Backend merges two owner-scoped sources — `Document` rows, and `Generation` rows with
   **no** linked document — applies search and sort, returns one offset-paginated page.
4. Client renders the feed in the last-chosen view; the choice persists across reloads.
5. «Недавние проекты» renders the first 4 items of the same fetched page — no second request.
6. User types in search; client debounces, re-requests from page 1 with `q`.
7. User picks a sort order (created ↓/↑, updated ↓, title А-Я, document type); client
   re-requests from page 1 keeping `q`.
8. Clicking a document card opens it in the editor (existing route).
9. Clicking «Повторить» on a failed/stalled generation card starts a new generation with the
   same parameters (`POST /generations/{id}/repeat` — no client-supplied idempotency key).
10. Empty feed shows one of two distinct states: "no matches for query" or "no work yet".

## Acceptance Criteria

### Feed contents & authorization

- `GET /api/v1/projects` returns only the caller's items; `owner_id` is a SQL predicate, never
  a request parameter. A foreign item is absent, not 403 — byte-identically to a nonexistent
  one. «Повторить» resolves its source under the same predicate.
- The feed contains every `Document`, plus only those `Generation`s with no linked `Document`
  — a converted generation appears exactly once, as its document.
- **Seam guard (merge snapshot):** with a `POST /documents/from-generation` committing
  concurrently with a `GET /projects`, the page contains that item exactly once — never zero
  times, never twice. Both sources are read in one query/transaction.
- **Seam guard (legacy rows):** a generation converted before story 18's `generation_id`
  column existed (link null) must not surface twice — a back-fill migration runs, or a count
  assertion proves no such rows exist. Distinct from the snapshot guard above.
- Items carry `kind` (`document`|`generation`) and a string/UUID `id`; the client keys on
  `(kind, id)` and never infers kind from shape. An id above 2^53 round-trips byte-identically.
- An unrecognised `kind`, or a generation status outside the known set, renders as a neutral
  non-interactive card without «Повторить» (deny by default) and never blanks the feed.

### Sorting, search & paging

- Four criteria, five orders, working with and without an active `q`. Every sort is **total**,
  tie-broken on `(kind, id)` — not `id` alone: a document and a generation seeded with the
  same id value and the same `created_at` still order stably across pages and instances.
- Both arms project every sort key: a generation's `title` is its topic, its `document_type`
  the type it was requested with, its `updated_at` equal to its `created_at`. No sort is
  defined over a column only one arm has.
- Ordering collation is pinned in the query (`COLLATE "ru-RU-x-icu"`) — a mixed
  Cyrillic/Latin/mixed-case fixture asserts one exact order, and a hostile-locale (Turkish
  dotless ı) case-fold asserts matching is locale-invariant. The collation's **availability**
  is asserted at boot: a database without ICU fails loudly at startup, not per request.
- Untitled documents (`title` null) sort **last** under `title_asc` and render their
  `preview` instead of a title.
- Search is case-insensitive over title, generation topic, and document text; **both sides**
  are NFC-normalized, so a title stored in NFD is found by its NFC form and vice versa.
- No matches → 200 with empty `items` and a correct `total`; never 404, never an error.
- `page` above `projects_page_max` → 422 and no deep-offset scan; the deepest legal page
  completes in the same wall-clock bound as `page=1`, and `(page − 1) × limit` never wraps.
  A page past the end of the filtered set is an empty page, not an error.
- **Accepted paging degradation is pinned, not silent:** read page 1, insert a row sorting
  into the fetched window, read page 2 — the item is skipped (never duplicated), bounded to
  one per insert, so a later paging change goes red.

### Projection & rendering

- The response is a summary projection: no full `content`. `preview` is derived
  **server-side** from the stored (sanitized-HTML) content — markup stripped to plain text
  **before** truncation, so no cut emits an unbalanced tag or a re-injectable fragment.
  Truncation is bounded in code points and snaps back to a grapheme boundary: a ZWJ emoji
  sequence or a combining-accent letter astride the limit yields no replacement character,
  lone combining mark, or orphaned ZWJ.
- `preview`, `title`, and the echoed search query are escaped at render in every surface
  (grid card, list row, search header): a document titled `<script>alert(1)</script>`
  appears as text in the emitted markup.
- `created_at`/`updated_at` are stored and compared in UTC, converted to the viewer's zone at
  render only, through an injectable clock: an item created at `23:30+03:00` renders under the
  local date, and `created_desc` across a local-day boundary orders identically under UTC and
  non-UTC test zones.
- The list surface renders the three non-happy states the mockups omit — loading (skeleton),
  request error (retry action, no silent blank), partial/slow load — and two distinct empty
  states: "no matches" (reset search) and "no work yet" (create a project).
- Business document types and the «Учебные / Деловые» tabs render **inert** — not clickable,
  not focusable, disabled to assistive tech.

### Client behaviour

- View toggle and sort choice survive reload (per-device client storage); a corrupt persisted
  value falls back to the default view rather than rendering nothing.
- `q`, `sort`, `page` and view are reflected in the feed URL: opening a card and navigating
  back, or refreshing, re-renders the same filtered feed — not a reset page-1 list.
- Search, sort and page changes are race-safe: a slower earlier response never overwrites a
  newer one, and a request for stale criteria is discarded client-side **and** cancelled
  server-side (see the bounds below).
- «Повторить» is **not** optimistic: no new card renders until the repeat response confirms
  it. On failure the feed returns to its exact pre-click state with an inline retry-able error
  on the original card — no phantom card survives a reload. Each failure mode is asserted:
  timeout, 4xx (surface, no auto-retry), 5xx (surface with retry), malformed body.
- After one click and after a double-click alike, the feed holds exactly one original card and
  exactly one new card.
- The feed's error-state retry uses a capped attempt count with exponential backoff plus
  jitter — never a fixed-tick hammer against a failing dependency.

### Repeat («Повторить») server semantics

- The operation's identity is the **source generation**, addressed by id
  (`POST /generations/{id}/repeat`) — no client-supplied `Idempotency-Key`. A key the browser
  mints per click (today `crypto.randomUUID()` in `generationApi.ts`) collapses neither a
  double-click, nor a second tab, nor a retry after a lost response.
- At most one repeat of a source is outstanding, enforced by a DB uniqueness constraint over
  non-failed children (`repeat_of_generation_id`), never an in-memory store. Two concurrent
  repeats released together at a latch across instances create exactly one `Generation` and
  return the same id (201 first, 200 replay).
- Repeat-after-repeat still works: once a repeat has itself **failed** it is no longer
  outstanding, so a second repeat creates a second child — collapsing it would leave the user
  clicking a button that silently does nothing. A guard asserts it.
- The server re-reads the source's status at command time; the rendered card is not trusted.
  A source that has since completed and become a document → 409 `NOT_REPEATABLE` carrying its
  current status so the client refreshes — never a second generation. A generation in
  `pending`/`in_progress` past `generation_stale_after` is presented as `stale` and
  repeatable; before the deadline it is not (409). The accepting states are enumerated, and
  `can_repeat` is **server-computed** — a client must not derive it from an enum it may not
  fully know.
- The repeat carries no body: every parameter is copied from the source row, so there is no
  `ownerId`, `id`, `status`, or document link for a client to over-bind. A body is ignored.

### Bounds, operability & disclosure

- The `ILIKE` search path is bounded server-side: `q` length cap, a statement timeout
  **strictly below** the gateway/client read timeout, and cancellation of a superseded or
  client-aborted query — an abandoned search leaves nothing executing after the caller gave
  up. Every exit path, timeout included, releases its pooled connection: a burst of superseded
  searches returns pool checkout to baseline. The client debounce is not counted as a bound.
- If either source arm of the merged read fails, the request fails as a whole — the feed never
  renders a silently half-populated page. The search-timeout/abort branch emits a
  distinguishable log signal (owner id, query length) and a counter; the happy path emits
  neither.
- `total` rides the same `ILIKE` predicate as the page query, so it shares that path's
  statement timeout and cancellation — it is not a second unbounded count per keystroke.
- Every environment-varying value is a named config key with an explicit default, pinned in
  `api-specs/projects_list.yaml` (`x-config`): timeout 3000 ms, `q` 200 chars, `preview` 200
  code points, page size 20/50, **page ceiling 500**, recent items 4, collation `ru-RU-x-icu`,
  plus the staleness deadline and the debounce interval. Booting with any unset fails fast
  naming the key, rather than running an untimed sequential scan.
- Error bodies for **every** failure family (401/422, search timeout, unexpected 5xx) use the
  project's generic shape; a seeded sentinel never reaches the response, and reaches logs only
  as a fixed redaction token keyed by a correlation id.

## Validation Rules

| Field | Rule |
|-------|------|
| `q` | optional; trimmed; NFC-normalized; max 200 chars (`projects_search_query_max_chars`) → 422 above; empty/whitespace-only ≡ absent; `%`, `_` and the escape character itself escaped via `ESCAPE '\'`, never pattern syntax; `\r\n` never forges a log line |
| `sort` | optional enum: `created_desc` (default) \| `created_asc` \| `updated_desc` \| `title_asc` \| `type_asc`; unknown value → 422, never silent fallback |
| `page` | integer ≥ 1, default 1; non-integer/≤0 → 422; above `projects_page_max` (500) → 422 — at the ceiling and at ceiling+1 both behave definedly, and `(page − 1) × limit` never wraps |
| `limit` | integer 1…50, default 20; above max → 422 (not silently clamped) |
| Authorization | Bearer required; missing/invalid → 401; token verification erroring or timing out resolves to 401, never to a served feed |
| `preview`, `kind`, `owner_id` | server-derived only; a client-supplied value is rejected, not merged |

## Screen States

- **Feed — grid view** — card tiles with type folder icon, title/preview, date.
- **Feed — list view** — same data as rows; `···` menu drawn inert (story 11).
- **Recent projects section** — first 4 of the same page.
- **Search active — results** — feed filtered, query visible, clear-query control.
- **Search active — no matches** — action: reset search.
- **Empty — no work yet** — action: create a project.
- **Loading** — skeleton for the feed region.
- **Load error** — message + retry, feed region only (page chrome stays).
- **Generation card — failed / unfinished / stale** — status text + «Повторить».
- **Mobile grid** — single-column layout (`mockups/mobile/01-projects-grid.html`).

## Core Requirements

- Contracts: `api-specs/projects_list.yaml` (+ `projects_schemas.yaml`),
  `api-specs/generations_repeat.yaml`; index in `endpoints.md`.
- The two existing list endpoints are not extended (their keyset anchor must stay immutable —
  see `interview.md`); they are marked `deprecated: true` and keep working, and the `/{id}`
  singles are untouched. One usecase owns the merged read and does not call the
  document/generation list usecases.
- Offset pagination is a deliberate trade (deep pages scan linearly); revisit when one owner's
  item count reaches thousands. Sort keys `updated_at`/`title`/`type` are only safe because of
  it — no keyset cursor may later be introduced over a mutable column without re-deciding this.
- Document-text search uses `ILIKE` without a full-text index — accepted debt (no morphology,
  degrades with volume), recorded in `.memory-bank/tasks/known-debt.md`; replacement is
  `tsvector` + GIN with a Russian configuration.
- Response-shape evolution: old frontend builds tolerate the new `preview`/`kind` fields, and
  the new frontend tolerates `preview: null` during a rolling deploy.
- Frontend reuses `frontend/src/features/history/` (`HistoryPage`, `useHistoryList`,
  `historyApi`) rather than adding a parallel list stack; grid rendering and the view toggle
  are new. Out of scope, drawn inert: category tabs, `···` actions (story 11), business types.
- `Generation` gains a nullable `repeat_of_generation_id` column (+ migration, + partial unique
  index over non-failed children) — the constraint the repeat's exactly-once rule rests on.
- ACTION (`/test-spec`): pin «Недавние проекты» behaviour under an active search or a
  non-default sort. ACTION (design): эссе and сочинение have no icon in
  `Cards/Images color folders` — both currently show the teal folder.
