# Мои проекты (list / search / sort, grid + list view)

## Brief Description

One owner-scoped feed of the user's work — documents plus generations that never became
documents (failed/unfinished) — with search, four sort orders, and a grid/list view
toggle, served by a new `GET /api/v1/projects`.

## Flow

1. User opens «Мои проекты».
2. Client calls `GET /api/v1/projects?page&limit&sort&q` (Bearer required).
3. Backend merges two owner-scoped sources — `Document` rows, and `Generation` rows with
   **no** linked document — applies search and sort, returns one offset-paginated page.
4. Client renders the feed in the last-chosen view (grid or list); the choice persists per
   user across reloads.
5. «Недавние проекты» renders the first N items of the same fetched page — no second request.
6. User types in search; client debounces, re-requests from page 1 with `q`.
7. User picks a sort order (created ↓/↑, updated ↓, title А-Я, document type); client
   re-requests from page 1 keeping `q`.
8. Clicking a document card opens it in the editor (existing route).
9. Clicking «Повторить» on a failed/unfinished generation card starts a new generation with
   the same parameters (`POST /generations`, `Idempotency-Key`).
10. Empty feed shows one of two distinct states: "no matches for query" or "no work yet".

## Acceptance Criteria

### Feed contents & authorization

- `GET /api/v1/projects` returns only the caller's items; `owner_id` is a SQL predicate,
  never a request parameter. Another account's item is absent, not 403 — absent and
  non-existent are byte-identical.
- «Повторить» resolves its source generation under the same owner-scoped predicate: a
  repeat naming another owner's generation id responds identically to one naming a
  nonexistent id, and creates nothing.
- The feed contains every `Document`, plus only those `Generation`s with no linked
  `Document` — a converted generation appears exactly once (as its document).
- **Seam guard (merge snapshot):** with a `POST /documents/from-generation` committing
  concurrently with a `GET /projects`, the returned page contains that item exactly once —
  never zero times, never twice. Both sources are read in one query/transaction.
- **Seam guard (legacy rows):** a generation converted before story 18's `generation_id`
  column existed (link null) must not surface twice. Either a back-fill migration runs, or
  a count assertion proves no such rows exist. Distinct from the snapshot guard above.
- Every list item carries a stable `id` and its `kind` (`document`|`generation`); the client
  keys on `(kind, id)` and never infers kind from shape. `id` is serialized as a string /
  UUID — an id above 2^53 round-trips byte-identically to the client.
- An item with an unrecognised `kind`, or a generation with a status outside the known set,
  renders as a neutral non-interactive card without the «Повторить» action (deny by
  default) and never blanks the feed region.

### Sorting, search & paging

- Four sorts work with and without an active `q`: `created_desc`, `created_asc`,
  `updated_desc`, `title_asc`, `type_asc`. Every sort is **total** — an `id` tie-breaker is
  appended so equal values give a stable, repeatable order across pages and instances.
- Ordering collation is pinned **in the query** (`COLLATE "ru-RU-x-icu"`), never inherited
  from the database, session, or dump — a fixture mixing Cyrillic, Latin and mixed-case
  titles asserts one exact order. Case-insensitive matching is locale-invariant (asserted
  under a hostile locale, e.g. Turkish dotless ı).
- Untitled documents (`title` null) sort **last** under `title_asc` in either direction, and
  render their `preview` instead of a title.
- Search is case-insensitive over title, generation topic, and document text. **Both sides**
  of the comparison are NFC-normalized at query time: a title stored in NFD is found by its
  NFC form and vice versa.
- Search matches nothing → 200 with empty `items` and correct `total`, never 404, never an
  error.
- Paging is offset-based: `page`/`limit` with a server-enforced max on both. An out-of-range
  `page` returns an empty page; `page` above the pinned ceiling returns 422 and never
  executes a deep-offset scan — `page` at the ceiling completes in the same wall-clock bound
  as `page=1`, and `(page − 1) × limit` never wraps to a negative offset.
- **Accepted paging degradation is pinned, not silent:** read page 1, insert a row sorting
  into the fetched window, read page 2 — the observed skip-or-duplicate matches the
  documented choice and is bounded to one item, so a later paging change goes red.

### Projection & rendering

- The response is a summary projection: no full `content`. `preview` is derived
  **server-side** from the stored (sanitized-HTML) content: markup is stripped to plain text
  **before** truncation, so no cut can emit an unbalanced tag or a re-injectable fragment.
- Truncation is bounded in Unicode code points and snaps back to a grapheme boundary — a
  ZWJ emoji sequence or a combining-accent Cyrillic letter astride the limit yields no
  replacement character, lone combining mark, or orphaned ZWJ.
- `preview`, `title`, and the echoed search query are escaped at render in every surface
  (grid card, list row, search header): a document titled `<script>alert(1)</script>`
  appears as text in the emitted markup.
- `created_at`/`updated_at` are stored and compared in UTC and converted to the user's local
  zone at render only, through an injectable clock: an item created at `23:30+03:00` renders
  under the local date, and `created_desc` across a local-day boundary orders identically
  under UTC and non-UTC test zones.
- The list surface renders three non-happy states the mockups omit: loading (skeleton),
  request error (retry action, no silent blank), and partial/slow load.
- Two empty states, not one: "no matches" (action: reset search) and "no work yet" (action:
  create a project).
- Business document types and the «Учебные / Деловые» tabs render **inert** — not clickable,
  not focusable, disabled to assistive tech.

### Client behaviour

- View toggle and sort choice survive reload (per-device client storage); a corrupt persisted
  value falls back to the default view rather than rendering nothing.
- `q`, `sort`, `page` and view are reflected in the feed URL: opening a card and navigating
  back, or refreshing, re-renders the same filtered feed — not a reset page-1 list.
- Search, sort and page changes are race-safe: a slower earlier response never overwrites a
  newer one, and an in-flight request for stale criteria is discarded client-side **and**
  cancelled server-side (see resource bound below).
- «Повторить» is **not** optimistic: no new card renders until the `POST /generations`
  response confirms it. On failure the feed returns to its exact pre-click state with an
  inline retry-able error on the original card — no phantom card survives a reload. Each
  failure mode is defined and asserted: timeout, 4xx (surface, no auto-retry), 5xx (surface
  with retry), malformed body.
- After one click and after a double-click alike, the feed contains exactly one original card
  and exactly one new card (this resolves the open ACTION about the old card).
- The feed's error-state retry uses a capped attempt count with exponential backoff plus
  jitter — never a fixed-tick hammer against a failing dependency.

### Repeat («Повторить») server semantics

- Two `POST /generations` with the same `Idempotency-Key` — sequential replay **or** two
  concurrent requests across instances, released together at a latch — create exactly one
  `Generation` row and return the same id. Exclusion is a DB unique constraint / conditional
  insert, never an in-memory store. The client-side single-fire is a UX nicety, not the guard.
- The server re-reads the generation's status at command time: a repeat targeting a
  generation that has since completed and linked a document is rejected as a stale-state
  no-op (409, feed refreshed), never a second generation.
- A generation stuck in `pending`/`in_progress` past a pinned staleness deadline is presented
  as failed-and-repeatable; before the deadline it is not repeatable. Which source states
  accept «Повторить» is enumerated, and every other state rejects with no `POST` issued.
- The repeat body binds an explicit allow-list of generation parameters; `ownerId`, `id`,
  `status`, or a document link in the body never reach storage — the persisted generation is
  owned by the caller and starts in the initial state.

### Bounds, operability & disclosure

- The `ILIKE` search path is bounded server-side: pinned `q` max length, a statement timeout
  set **strictly below** the gateway/client read timeout, and cancellation of a superseded or
  client-aborted query — an abandoned search leaves no query still executing after the caller
  gave up. Every exit path, including the timeout branch, releases its pooled connection;
  a burst of superseded searches returns pool checkout to baseline. The client debounce is
  not counted as a bound.
- If either source arm of the merged read fails, the request fails as a whole — the feed
  never renders a silently half-populated page.
- The search-timeout/abort branch emits a distinguishable log signal (owner id, query length)
  and increments a counter; the happy path emits neither.
- Every environment-varying value — search statement timeout, `q` max length, `preview`
  length, page-size default and max, recent-items `N`, debounce interval — is a named config
  key with an explicit default; booting with the statement timeout unset fails fast and names
  the key, rather than running an untimed sequential scan.
- Error bodies for **every** failure family (401/422, search timeout, unexpected 5xx) use the
  project's generic shape; a seeded sentinel never appears in the response, and appears in
  logs only as a fixed redaction token keyed by a correlation id.

## Validation Rules

| Field | Rule |
|-------|------|
| `q` | optional; trimmed; NFC-normalized; max length pinned (named config key); empty/whitespace-only ≡ absent; `%`/`_` escaped as literals, never pattern syntax; `\r\n` never forges a log line |
| `sort` | optional enum: `created_desc` (default) \| `created_asc` \| `updated_desc` \| `title_asc` \| `type_asc`; unknown value → 422, never silent fallback |
| `page` | integer ≥ 1, default 1; non-integer/≤0 → 422; bounded by a pinned ceiling within a pinned integer type — at ceiling and ceiling+1 both behave definedly, no wrapped offset |
| `limit` | integer 1…50, default 20; above max → 422 (not silently clamped) |
| Authorization | Bearer required; missing/invalid → 401; token verification erroring or timing out resolves to 401, never to a served feed |
| `preview`, `kind`, `owner_id` | server-derived only; a client-supplied value is rejected, not merged |

## Screen States

- **Feed — grid view** — card tiles with type folder icon, title/preview, date.
- **Feed — list view** — same data as rows; `···` menu drawn inert (story 11).
- **Recent projects section** — first N of the same page.
- **Search active — results** — feed filtered, query visible, clear-query control.
- **Search active — no matches** — action: reset search.
- **Empty — no work yet** — action: create a project.
- **Loading** — skeleton for the feed region.
- **Load error** — message + retry, feed region only (page chrome stays).
- **Generation card — failed / unfinished / stale** — status text + «Повторить».
- **Mobile grid** — single-column layout (`mockups/mobile/01-projects-grid.html`).

## Core Requirements

- New `GET /api/v1/projects`; the two existing list endpoints are not extended (their keyset
  anchor must stay immutable — see `interview.md`) and are marked `deprecated: true` while
  continuing to work. `GET /{id}` singles are untouched. One usecase owns the merged read; it
  does not call the document/generation list usecases.
- Offset pagination is a deliberate trade (deep pages scan linearly). Revisit when a single
  owner's item count reaches thousands. Sort keys `updated_at`/`title`/`type` are only safe
  because paging is offset-based — no keyset cursor may later be introduced over a mutable
  column without re-deciding this.
- Document-text search uses `ILIKE` without a full-text index — a knowingly accepted debt
  (no morphology, degrades with volume), recorded in `.memory-bank/tasks/known-debt.md`;
  replacement is `tsvector` + GIN with a Russian configuration.
- Response-shape evolution: old frontend builds tolerate the new `preview`/`kind` fields, and
  the new frontend tolerates `preview: null` during a rolling deploy.
- Frontend reuses `frontend/src/features/history/` (`HistoryPage`, `useHistoryList`,
  `historyApi`) rather than adding a parallel list stack; grid rendering and the view toggle
  are new.
- Out of scope, drawn inert: category tabs, `···` document actions (story 11), business
  document types.
- ACTION (`/test-spec`): pin «Недавние проекты» behaviour while search is active or sort is
  non-default.
- ACTION (design): icons for эссе and сочинение are missing from `Cards/Images color folders`
  — both currently show the teal folder.
