# Мои проекты — Acceptance Criteria

Split out of `12_MyProjects.md` to keep both files under the 200-line limit. These are the
story's testable criteria; the flow, validation table, screen states and core requirements
live in the main file.


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
- A generation non-terminal longer than `GENERATION_STALE_AFTER_MINUTES` is presented as
  **recovering**, and is **not** retryable — the existing `RequeueStaleGenerations` sweep owns
  recovery, and a user retry there would run live work a second time. A test ages a pending
  row past the threshold and asserts the card changes label but keeps `retryable: false`.
- Each item carries `kind` and a stable opaque `id`. **The item key is the pair `(kind, id)`** —
  `Document.id` and `Generation.id` are separate UUID spaces. Two rows of different kinds sharing
  a UUID are two distinct items and survive client dedupe.
- An unknown/newly-added `Generation` status fails closed to `status: "unknown"` and is never
  mapped to a displayed one. `kind` stays the source discriminator (`document`|`generation`) —
  it must not encode status, or a new status would change a row's identity and its sort
  position, since `(kind, id)` is the item key and the tiebreak.
- A `document_type` not in the pinned order table sorts last, deterministically, and renders a
  fallback icon — it never crashes the projection. (Story 1 adds types in a parallel worktree.)
- An untitled document is labelled by its `preview` first line, not by its type — the bug fixed
  in `b6ee9fa` was every row being named after its type and so being unopenable.

### Sorting & paging

- `sort` accepts exactly `created_desc` (default), `created_asc`, `updated_desc`, `title_asc`,
  `type_asc`; any other value → 400, never a silent fallback.
- Every sort is **total and stable**: the sort key is followed by a `(kind, id)` tiebreak. Two
  rows with an equal sort key return the same order on repeated reads.
- Untitled rows sort **last** under `title_asc`, which reads `documents.title` and
  `generations.topic`; `type_asc` uses an explicit server-side type order, not raw Cyrillic byte
  order, over the NOT NULL `document_type` both tables carry. `updated_desc` reads the
  `updated_at` both tables already have — generations' is storage-owned, maintained for the
  sweep, so no kind sinks to the tail of the feed.
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
  response, and the **projection** reads only a bounded prefix of `content` from the database —
  the bytes *returned* per page are bounded by `limit × preview_max`, independent of stored
  document size. (The bound is on the projection, not on the scan: a `q` search still reads full
  bodies to match them — that is the unindexed-`ILIKE` cost, bounded by the timeout below.)
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

- Retry is `POST /api/v1/generations/{id}/retry` with **no body** — the source is named by id and
  its parameters are copied server-side, so there is no field a client could over-bind.
- Two retries carrying the same `Idempotency-Key` — concurrent, arriving at different instances —
  yield **exactly one** `Generation`. Uniqueness is on **`(owner_id, Idempotency-Key)`**, enforced
  by a database constraint: keying on the header alone lets one account's replay return another
  account's row. A client-side in-flight lock is a UI affordance and does not satisfy this.
- A retry whose response is lost and is re-sent with the same key creates no second generation.
  A *new* attempt after the previous one reached a terminal state uses a **fresh key** and does
  create a new generation — the button never goes silently dead. The same key against a
  *different* source id is 409, not a silent replay of the first.
- Retrying a generation owned by another account, or a nonexistent one, returns a byte-identical
  404. Retrying a `pending`/`in_progress`/`completed` source is 409 `NOT_RETRYABLE`.
- A failed retry (timeout / 4xx / 5xx) is **distinguishable from success**: the card surfaces the
  error, the in-flight lock is released so a second «Повторить» is possible, and no phantom
  pending row is left behind.
- The old failed card is **kept** alongside the new generation — nothing is deleted or mutated,
  so the next `GET /projects` shows exactly two rows for the retried work.

### Failure & disclosure

- The feed response is `Cache-Control: no-store` — it is account-specific and must not be held
  by a shared cache.
- A searching request is capped at **one in flight per account** (429 `SEARCH_BUSY` above it).
  The debounce is in the browser and does nothing for a second tab or a scripted client, and
  cancelling an HTTP request does not cancel the database scan it started.
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
- «Повторить» is **not optimistic**: no new card renders until the retry response confirms it.
  On failure the feed returns to its exact pre-click state with an inline retryable error on the
  original card — no phantom card survives a reload. Each failure mode is asserted separately:
  timeout, 4xx (surface, no auto-retry), 5xx (surface with retry), malformed body.
- The feed's error-state retry uses a **capped attempt count with exponential backoff plus
  jitter** — never a fixed-tick hammer against a failing dependency.
- A corrupt persisted view preference falls back to the default view rather than rendering
  nothing.
- `retryable` is **server-computed** and never derived client-side from `status`: a client
  computing it from an enum it may not fully know would offer «Повторить» on an unknown status,
  which is fail-open.
- The category tabs, the `···` actions menu, and the business document types render **inert** —
  not clickable, not focusable, and disabled to assistive tech.

### Operability & rolling deploy

- The pinned ordering collation's **availability** is asserted at boot: a database without it
  fails loudly at startup, not per request.
- The accepted offset-paging degradation is **pinned, not silent**: read page 1, insert a row
  sorting into the fetched window, read page 2 — the item is **skipped, never duplicated**, and
  bounded to one per insert, so a later paging change goes red rather than quiet.
- Response-shape evolution is tolerated both ways during a rolling deploy: old frontend builds
  ignore the new `preview`/`kind` fields, and the new frontend tolerates `preview: null`.
- If either source arm of the merged read fails, the request fails **as a whole** — the feed
  never renders a silently half-populated page. The timeout/abort branch emits a distinguishable
  log signal (owner id, query length) and a counter; the happy path emits neither.
- `total` rides the same predicate as the page query, so it shares that path's statement timeout
  and cancellation — it is not a second unbounded count per keystroke.

