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
9. Clicking «Повторить» on a failed-generation card starts a new generation with the same
   parameters (`POST /generations`, story 1) carrying an `Idempotency-Key`.
10. Empty result renders one of two distinct states: "no matches" or "no projects yet".

## Acceptance Criteria

### Feed composition

- `GET /api/v1/projects` requires a Bearer access token → 401 otherwise; `owner_id` is a query
  predicate, never a request parameter. Another account's rows are absent from every page under
  every `q`/`sort`/`page` combination.
- **Every `Generation` status has an enumerated feed outcome** — surfaced as a generation card,
  suppressed because a `Document` exists, or suppressed entirely. Seeding one row per status
  asserts each outcome. In particular a generation that **completed but has no linked
  `Document`** is surfaced, not silently dropped: that row is exactly the "disappears without a
  trace" case the story exists to fix.
- A `Generation` that already has a linked `Document` appears **once**, as the document. After a
  generation completes, the next list request shows it once as a document — never simultaneously
  as a stale generation card and a document row.
- A generation that has been non-terminal longer than a named age is presented as **stalled**
  (retryable), not as still running. A test ages a pending row past the bound and asserts the
  card changes state.
- Each item carries `kind` and a stable opaque `id`. **The item key is the pair `(kind, id)`** —
  `Document.id` and `Generation.id` are separate UUID spaces. Two rows of different kinds sharing
  a UUID are two distinct items and survive client dedupe.
- An unknown/newly-added `Generation` status fails closed to `kind: "unknown"` (a contract value,
  enumerated alongside `document` and `generation`) and is never mapped to a displayed status.
- A `document_type` not in the pinned order table sorts last, deterministically, and renders a
  fallback icon — it never crashes the projection. (Story 1 adds types in a parallel worktree.)

### Sorting & paging

- `sort` accepts exactly `created_desc` (default), `created_asc`, `updated_desc`, `title_asc`,
  `type_asc`; any other value → 400, never a silent fallback.
- Every sort is **total and stable**: the sort key is followed by a `(kind, id)` tiebreak. Two
  rows with an equal sort key return the same order on repeated reads.
- Untitled rows sort **last** under `title_asc`; `type_asc` uses an explicit server-side type
  order, not raw Cyrillic byte order, and untyped generation cards sort last.
- `title_asc` ordering and `q` case-folding are pinned to an **explicit collation / normalized
  sort key**, not the database's ambient locale. A mixed case / Cyrillic / Latin fixture yields
  the identical order and the identical matches on a database created with a different default
  locale.
- Paging a static set returns each row exactly once and misses none:
  `sum(len(items))` over all pages equals `total` exactly, asserted with a
  generation-that-has-a-document present so a double-count would change the number, and at
  `total = 0`.
- `items` and `total` come from **one consistent read snapshot**; mutating the owner's rows
  between two internal reads cannot produce a response where `total` and the page disagree.
- A `page` past the end returns empty `items` with the real `total` — not a 404.
- A committed write is visible to the very next `GET /api/v1/projects` (read served with the
  write's commit visible) — a replica-lagged pre-write page is a failure.

### Input validation

- `page` and `limit` are parsed as **exact decimal integers**: `2.5`, `1e3`, `+1`, `0x10`, or a
  value past the integer type max → 400, never truncated or wrapped.
- `page` has a **named maximum** (above it → 400) so `(page-1) * limit` cannot overflow the
  offset type and cannot be used as a deep-scan lever.
- `q` is bounded at 200 **Unicode code points** (not bytes), decoded as UTF-8, asserted at the
  boundary with multibyte content where byte and code-point length differ.
- `q` searches title, generation topic, and document content, case-insensitively, NFC-normalized
  on both sides. Whitespace-only `q` behaves as no search. `%`, `_`, and `\` in `q` match
  literally.
- Search combines with sort and paging: `q` + non-default `sort` + `page=2` returns the second
  page of the *filtered* set, and `total` is the filtered count.

### Preview & output encoding

- Each item carries a server-derived `preview` (plain text). Full `content` is never in the
  response, and the query reads only a **bounded prefix of `content` from the database** — bytes
  read per page are bounded by `limit × preview_max`, independent of stored document size.
- `preview` length is measured in Unicode code points against a named constant and **trims back**
  rather than splitting a grapheme cluster or a multibyte sequence.
- `preview`, `title`, and generation `topic` are all emitted neutralized — a document saved with
  `<script>` in its title, or a generation with markup in its topic, reaches the renderer inert.
  Asserted per field, not only for `preview`.
- Timestamps are UTC ISO-8601 with an explicit offset; two rows created either side of local
  midnight sort by the same canonical instant regardless of server zone.
- «Недавние проекты» membership is the **first N of the sorted page** by an explicit rule — not a
  time window — and the section is hidden when `q` is active or `sort` is not the default.

### Retry («Повторить»)

- Two `POST /generations` carrying the same `Idempotency-Key` — concurrent, arriving at different
  instances — yield **exactly one** `Generation`, enforced atomically in the database. A
  client-side in-flight lock is a UI affordance and does not satisfy this.
- A retry whose response is lost and is re-sent with the same key creates no second generation.
  A *new* attempt after the previous one reached a terminal state uses a **fresh key** and does
  create a new generation — the button never goes silently dead.
- Retrying a generation owned by another account is denied with the same response as an unknown
  id. Server-owned fields in the retry body (`owner_id`, `id`, `status`, `created_at`) are
  ignored — the new generation is persisted with the caller as owner and a server-assigned status.
- A failed retry (timeout / 4xx / 5xx) is **distinguishable from success**: the card surfaces the
  error, the in-flight lock is released so a second «Повторить» is possible, and no phantom
  pending row is left behind.
- The old failed card's post-retry state is pinned (kept alongside, or replaced) so the next
  `GET /projects` has an assertable row count for the retried work.

### Failure & disclosure

- The projects query carries a finite statement timeout. On trip it returns the generic
  `{error_code, message}` envelope with a correlation id — no stack frame, SQL keyword, internal
  class name, or file path in the body; the underlying error goes to the log under that id.
- When token validation or owner resolution errors or times out, the request is **denied**
  (401/503) — never served as an unscoped or empty-but-200 feed.
- A by-id open or retry of another account's `(kind, id)` returns byte-identical status and body
  to a nonexistent id.
- The unknown-status branch emits a signal carrying the generation id **and** the unrecognized
  status value; the happy path emits nothing on that channel.

### Client behaviour

- The feed renders only the response of the **latest issued** list request: `q=A` then `q=B`
  resolving out of order leaves B's results on screen, and A's late arrival does not overwrite
  them. Superseded requests are cancelled or dropped.
- The search input is debounced at a named interval, with the superseded in-flight request
  cancelled — every keystroke firing an unindexed content scan is the endpoint's worst case.
- `q`, `sort`, `page`, and view mode survive opening a project and coming back, and survive a
  refresh (carried in the URL). Searching, paging to 3, and opening a card must not land the user
  back on an unfiltered page 1.
- `GET /documents` and `GET /generations` are marked `deprecated: true` in their contracts and
  behave exactly as before — no response-shape change, no new required parameter.

## Validation Rules

| Field | Rule |
|-------|------|
| Authorization | Bearer access token required; account resolved server-side → 401 if missing/expired/non-access; fail closed if the check itself errors |
| page | exact decimal integer, 1..`PAGE_MAX`, default 1; else 400 `INVALID_PAGE` |
| limit | exact decimal integer, 1..100, default 20; else 400 `INVALID_LIMIT` |
| sort | one of `created_desc`\|`created_asc`\|`updated_desc`\|`title_asc`\|`type_asc`; else 400 `INVALID_SORT` |
| q | optional; trimmed; ≤200 Unicode code points → else 400 `INVALID_QUERY`; NFC-normalized; LIKE metacharacters escaped |
| preview | server-derived only, never accepted from the client; DB-side prefix read, code-point bounded, plain text |
| Idempotency-Key | required on the retry `POST /generations`; uniqueness enforced in the database, not in process memory |

## Screen States

- **Grid view** / **List view** — same feed; the toggle is client-side only, no refetch, scroll
  position and active search preserved.
- **Recent projects** — first N of the same response; hidden under an active `q` or a non-default
  sort.
- **Search active, results** — filtered feed with a visible result count.
- **Search active, no matches** — action = clear the search.
- **No projects yet** — distinct empty state, action = create a project.
- **Failed / stalled generation card** — status + «Повторить»; retry-error variant with the button
  re-enabled.
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
- The unindexed scan needs a **named response-time bound** (not merely a recorded baseline) for a
  worst-case `q` against a seeded account, asserted in a load scenario, plus the stated behaviour
  above that bound.
- No in-memory state: no cached feed, `total`, page window, or idempotency record. Multi-instance
  deployment; the database is the only shared state.
- One new usecase (`ListProjects`) over one new repository port. It must not call the existing
  document/generation list usecases.
- Categories («Учебные / Деловые»), the `···` actions menu (story 11), and business document types
  are drawn but inert — no domain field, no endpoint, no behaviour in this story.
- ACTION (`/api-spec`): pin the old card's fate after «Повторить»; the `preview` length constant;
  the recent-section `N`; `PAGE_MAX`; the non-terminal stall age; the debounce interval; and the
  per-kind response schema.
- ACTION (design): icons for эссе and сочинение are missing from the kit — placeholder teal
  folders in the mockups.
