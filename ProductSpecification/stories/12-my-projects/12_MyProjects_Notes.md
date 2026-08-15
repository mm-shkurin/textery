# Мои проекты — Notes & Considerations

## Warnings

### Functional Warnings

- **Offset pagination over a live set.** A row created or edited between two page requests
  shifts every later row by one — the client sees a duplicate or misses a row. Not fixable
  with offset; the mitigation is client-side dedupe by `(kind, id)` and an honest note in the
  contract. The keyset alternative was rejected because `updated_at`/`title`/`type` are all
  mutable anchors (see `interview.md`).
- **Two sources, one identity space.** `Document.id` and `Generation.id` are separate UUID
  spaces. A merged feed keyed on `id` alone can, in principle, collide across the two
  tables; the item key must be `(kind, id)`, and the client's dedupe must use the pair.
- **The "recent projects" section duplicates rows** that also appear in "all projects" —
  that is what the mockup shows, and it is intentional. It stops making sense under an
  active search or a non-default sort; the spec hides it in those states.
- **Retry semantics on a failed generation** are half-specified until `/api-spec`: whether
  the old card stays or is replaced changes both the response shape and what the list does
  on the next poll.
- **A generation that completes while the user is on the list page** should stop being a
  "failed/unfinished" card and become a document — but the list is not live. The stale card
  stays until refresh. Acceptable; worth a note in the frontend scenarios.
- **Legacy converted generations may have a null link.** The feed rule is "generations with no
  linked document". A generation converted before story 18's `generation_id` column landed has
  that link null and would surface twice. Check the back-fill — or assert no such rows exist —
  before trusting the predicate. This is a *different* guard from the concurrent-conversion
  snapshot one; neither covers the other.
- **Search matches content the user cannot see.** A hit inside a 200 000-character document
  body returns a card whose title and preview contain none of the query text — it looks like
  a false positive. Consider surfacing a matched snippet later.

### UI/UX Warnings

- The two empty states are **not** interchangeable: "no matches" offers *clear the search*,
  "no projects yet" offers *create a project*. Shipping one for both is the classic error.
- Grid ⇄ list must not refetch, and must not lose scroll position or the active search.
- Loading and error states are absent from the mockups — design them before the frontend
  scenarios or they will be improvised per-component.
- Эссе and сочинение have no icon in the design kit; both render as a teal folder in the
  mockups. Business types and the «Учебные / Деловые» tabs are drawn inert — a user will
  click them; they must look disabled, not broken.
- Sorting by type shows a Cyrillic ordering that will look arbitrary to a user unless the
  server pins an explicit, product-decided order.
- The grid/list preference is per-device client storage. A corrupt stored value must fall back
  to grid, not render an empty region.

### Technical Warnings

- **Unindexed `ILIKE '%…%'` over `content`** cannot use a B-tree index — it is a sequential
  scan of every row the owner predicate admits, each row up to 200 000 characters. Fine at
  tens of rows, visibly slow at thousands. This is accepted debt, not an oversight; it needs
  a recorded response-time baseline so the trigger to fix it is measured, not felt.
- **Deep offset pages** cost linearly: `OFFSET 5000` makes the database walk 5000 rows it
  then discards. Compounded by the point above.
- **The merge must happen in SQL.** Fetching both tables into Python and sorting there
  reads the caller's whole history for every page request — an amplification bug that only
  shows up on the accounts that matter most.
- **Owner scoping is the security invariant.** It is a predicate in the same query, ANDed
  before anything else; a `q` or `sort` value must never be able to widen it. The existing
  list endpoints already follow this — inherit, do not reinvent.
- `q` goes into a `LIKE` pattern: `%`, `_`, and the escape character itself must be escaped,
  or a user's `%` silently becomes "match everything". Parameter binding prevents injection;
  it does **not** prevent metacharacter meaning.
- NFC-normalize both the query and the compared columns, or a Cyrillic composed/decomposed
  mismatch makes a visibly-identical string not match.
- Marking the two old endpoints `deprecated` must be contract-only. Any behaviour change
  breaks the frontend that still calls `GET /documents` today.
- Multi-instance deployment: no in-memory caching of the feed, of `total`, or of a page
  window. State lives in the database.
- **`key={id}` in React silently reuses a node** when a document and a generation share a UUID.
  Same reason the item key is `(kind, id)` — the collision is invisible until it corrupts a row.
- **Response-shape evolution.** Adding `preview` and `kind` to the projection: old frontend
  builds must tolerate unknown fields, and the new frontend must tolerate `preview: null`
  during a rolling deploy.
- The search path's statement timeout is infrastructure-adjacent (a DB setting or a per-query
  `SET LOCAL`). It belongs in `infra/`, never hand-set on a running database.

---

## Suggestions & Future Enhancements

### Functional Suggestions

- Matched-snippet highlighting once full-text search lands.
- Filter by document type / status as a first-class parameter (the tabs are the natural home
  once categories exist).
- Bulk selection + bulk delete, once story 11 lands the single-item actions.

### UI/UX Suggestions

- Persist the grid/list preference per account (profile, story 13) rather than per session.
- Show the result count next to an active search — it makes an unexpectedly small result set
  legible.
- (Debounce was a suggestion here and has been promoted to a requirement in the main spec —
  on this endpoint it is a scale guard, not a polish item.)

### Technical Suggestions

- `tsvector` + GIN with a Russian dictionary is the real fix for search; it also removes the
  case/morphology gap (`рефератов` ≠ `реферат` today).
- A materialized "projects" view (or a projection table maintained on write) would collapse
  the merge and make every sort indexable — worth it only if the row counts justify it.
- A single `projects` read model (view or table) is worth considering if the merged query grows
  more branches.
- Relative dates ("2 дня назад") in the list view, where the date column is narrow.
- Keyset pagination becomes viable again for the two immutable sort orders
  (`created_desc`/`created_asc`) if deep paging ever hurts before the full rewrite.

---

## Technical Notes

### Load Considerations

Per-account row counts are expected in the tens for a real user this quarter, so offset
paging and unindexed search are adequate. The two costs that grow are the content scan and
the deep-offset walk, and they grow on the same axis (rows per account). A load scenario
should record a baseline for `GET /projects` with a search term against a seeded account so
the debt has a number attached.

### Security Considerations

- **IDOR / owner scoping** — the whole story's risk surface. `owner_id` from the token, as a
  SQL predicate; never from a query parameter. Cross-account absence must be asserted for
  every combination of `q`, `sort`, and `page`, not just the default page.
- **Injection** — parameterized binding plus LIKE-metacharacter escaping; `sort` must map
  through a server-side allowlist to column names, never be interpolated into SQL.
- **Output encoding** — `preview` derives from stored HTML `content`; strip to plain text
  server-side so stored markup cannot reach a renderer through a new field.
- **Enumeration / disclosure** — `total` counts only the caller's rows; error bodies stay
  generic.
- **Fail closed** — an unrecognized `sort` is a 400, not a default; an unknown generation
  status maps to a neutral kind, not to a displayed one.

### Infrastructure Notes

No new infrastructure. The read endpoint itself needs no schema change — a `preview`
derived at query time avoids one, at the cost of computing it per request; materializing
it later would be a migration plus a backfill.

The story does carry one migration, for the retry path rather than the feed:
`generations` gains an `idempotency_key` column and
`uq_generations_owner_idempotency_key`. See `endpoints.md` — the contract has advertised
that header as required since story 1, and nothing has enforced it.

### Integration Notes

- «Повторить» reuses `POST /generations` (story 1) with an `Idempotency-Key` — no new
  external integration.
- Story 11 owns the `···` actions; story 18 owns the one-feed decision and the design
  system; story 1's parallel worktree adds document types. Only `document_type` as a value
  is shared — no file overlap.

---

## Hazard Catalogue Scan Record

Scanned 2026-08-01 against groups **1–8** — the full `_index.md` **Groups** list at scan time.
A group added later makes this record a strict subset and obliges a re-scan while the spec is
still being worked.

| Group | Verdict | Disposition |
|-------|---------|-------------|
| 1 Money/numbers/representation | 6 GAPs | Folded: `PAGE_MAX`, strict integer parse, `total` = sum over pages, `q` bounded in code points, case-fold collation pinned, `title_asc` collation pinned. Money class dismissed — no monetary value in the story. |
| 2 Re-run safety/ordering/atomicity | 4 GAPs | Folded: idempotency-key lifetime (fresh key after terminal), server-side outbound idempotency, `items`+`total` in one snapshot, per-failure-mode retry behaviour, statement timeout. Compute-then-commit and deadline-budget classes dismissed — one hop, no side-effect loop. |
| 3 Concurrency/consistency/distribution | 3 GAPs | Folded: DB-enforced cross-instance idempotency, read-after-write visible next request, completed-generation transition shows once, stalled non-terminal age bound. Lost update dismissed — the endpoint is read-only. |
| 4 Data lifecycle & schema | 4 GAPs | Folded: full status partition (the completed-without-document row was being dropped — the story's own reason for existing), stall deadline, post-retry card state pinned, unknown `document_type` policy, `kind: "unknown"` made a contract value. Destructive-ops class dismissed — pure read; re-fires at `/api-spec` if the old card is *replaced*. |
| 5 Request boundary & input | 5 GAPs | Folded: foreign-vs-absent id indistinguishable, retry ownership re-check, retry-body allowlist, `title`/`topic` neutralized alongside `preview`, auth fails closed when the check itself errors. Absent-vs-null class was already covered. |
| 6 Scale & resource limits | 5 GAPs | Folded: DB-side `preview` prefix read, named response-time bound (a baseline is not a guard), statement timeout, debounce promoted to a requirement, `(kind, id)` as the unique item key. |
| 7 Time/operability/disclosure | 6 GAPs | Folded: UTC ISO-8601 with offset, «Недавние» as first-N not a time window, attributable unknown-status signal with a silent happy path, failed-retry distinguishable, collation pinned, timeout/5xx envelope with a correlation id. |
| 8 Client/frontend | 3 GAPs | Folded: latest-request-wins rendering, failed-retry rollback, feed state (`q`/`sort`/`page`/view) surviving navigation and refresh via the URL. Grid⇄list toggle dismissed — no server effect. |

**Seam synthesis.** Retry idempotency was flagged by six passes each assuming another owned it;
the guard is server-side and database-enforced — the client in-flight lock explicitly does not
count. `items`+`total` consistency sits with the transaction boundary (group 2); cross-request
offset drift stays accepted. One statement-timeout requirement covers groups 2, 6, and 7. One
collation requirement covers groups 1 and 7 — the same test run against a differently-localed
database closes the config-drift half. `(kind, id)` closes the group 6 / group 8 contradiction,
where the main spec had said "dedupe by `id`" and these notes had said the pair; the pair is
correct and the spec was fixed. No GAP was dismissed without a reason; none remain open.

**Biggest catch:** the original draft's feed predicate ("failed or non-terminal") silently
excluded a generation that completed but never became a document — the precise row the story
exists to stop from disappearing.

---

## Additional Context

See `interview.md` (2026-08-01) for the full reasoning behind the new-endpoint decision, the
offset-vs-keyset trade, the `ILIKE` compromise, and the precedent from story 18 about
non-clickable rows. `mockups/README.md` lists every divergence between the mockups and the
current code, including the missing icons and the inert tabs.
