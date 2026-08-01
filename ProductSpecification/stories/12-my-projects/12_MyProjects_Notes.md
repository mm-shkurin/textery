# Мои проекты — Notes & Considerations

## Warnings

### Functional Warnings

- **Two empty states are not one.** "Ничего не найдено" (action: reset query) and "работ ещё
  нет" (action: create a project) are different screens. Collapsing them strands a new user
  on a search-reset button that does nothing.
- **Sort + search interaction.** Changing sort while `q` is active must keep `q` and reset to
  page 1. Keeping the page number is the classic bug: user lands on an empty page 4 of a
  3-page result and reads it as "nothing found".
- **«Недавние проекты» duplicates «Все проекты».** Accepted per mockup. Under an active
  search or a non-default sort the section loses its meaning — behaviour pinned at
  `/test-spec`.
- **Repeat («Повторить») semantics.** Whether the failed card disappears, stays, or is
  replaced changes what the user sees immediately after clicking. Unpinned → each layer will
  invent a different answer. `/api-spec` decides.
- **Converted generation must not double-appear.** The feed rule is "generations with no
  linked document". If the link column is null for legacy rows converted before story 18's
  `generation_id` landed, those will surface twice — check the back-fill before trusting the
  predicate.

### UI/UX Warnings

- Mockups draw no loading and no error state; without them the feed flashes empty and reads
  as "no work yet" on every cold load.
- Inert controls (category tabs, `···`, business types) must be visibly and semantically
  disabled. A control that looks live and does nothing costs the user a click to discover —
  the same failure story 18 removed the "Генерации" tab over.
- Grid/list toggle persistence: per-user, survives reload. A corrupt stored value must fall
  back to grid, not render an empty region.
- Untitled documents render a preview line, not "Без названия" — closer to how notes apps
  behave and matches the interview decision.
- Debounced search: an un-debounced input fires a request per keystroke over an `ILIKE` on
  `content` — the most expensive query in the story, at typing frequency.

### Technical Warnings

- **`ILIKE '%…%'` over `content`** (up to 200 000 chars/doc) cannot use a b-tree index. It is
  a sequential scan of the owner's documents on every keystroke-debounce. Bound it: query
  length cap, statement timeout, and `limit`. This is the story's dominant performance risk.
- **User-supplied `%` and `_`** are `LIKE` wildcards. Unescaped, `q = "%"` matches everything
  and turns search into a full scan; escape them as literals.
- **Offset pagination is unstable under concurrent writes** — a row inserted while the user
  pages can shift the window, showing an item twice or skipping one. Acceptable at this
  scale; not acceptable silently, so the total-order tie-breaker (`id`) is mandatory.
- **Merging two tables** with a `UNION ALL` + outer sort: the sort must run over the merged
  set, not per-source, or page boundaries interleave wrongly.
- **Ids collide across kinds.** Document `id` and generation `id` come from different tables.
  The client key must be `(kind, id)`; a React `key={id}` will silently reuse a node.
- **Response-shape evolution.** Adding `preview` and `kind` to the projection: old frontend
  builds must tolerate unknown fields, and the new frontend must tolerate `preview: null`
  during rolling deploy.
- Deprecating `GET /documents` while the frontend still calls it — deprecation is a contract
  marker only. Removal is a separate task after the frontend has actually migrated.

---

## Suggestions & Future Enhancements

### Functional Suggestions

- Categories «Учебные / Деловые» — needs a domain concept (field on the entity, or a
  type→category mapping in one domain place). Deliberately deferred to the story that also
  adds business document types, so it is decided once.
- `···` actions (rename / delete / duplicate) — story 11.
- Filter by type as a first-class filter, once `type_asc` sorting proves users want grouping.

### UI/UX Suggestions

- Highlight the matched fragment in search results.
- Keep the scroll position when returning from the editor to the feed.
- Show relative dates ("2 дня назад") in the list view where the column is narrow.

### Technical Suggestions

- Replace `ILIKE` with `tsvector` + GIN and a Russian text-search configuration; then
  "рефератов" finds "реферат" and cost stops scaling with content size. Recorded as debt.
- If deep paging ever hurts, the fix is not keyset over `updated_at` (impossible — mutable
  anchor) but a materialized feed table or search-engine index.
- Consider a single `projects` read model (view or table) if the merged query grows more
  branches.

---

## Technical Notes

### Load Considerations

Per `ExpectedLoad.txt` scale, an owner has tens of items; the merged query and offset paging
are comfortably fast. The one non-linear cost is full-text `ILIKE` over document content,
which grows with total stored characters, not item count — a user with 20 long документов is
already scanning millions of characters per keystroke-debounce.

### Security Considerations

- **IDOR** is the primary risk: `owner_id` from the token as a query predicate, never from
  the request. Foreign items are absent, not forbidden — absent and non-existent must be
  byte-identical.
- **Injection**: search text goes into `ILIKE` via bound parameters; wildcards escaped.
- **Mass assignment**: `preview`, `kind`, `owner_id` are server-derived; a client-supplied
  value is rejected, not merged.
- **Disclosure**: the list projection must not leak another user's counts via `total`, nor
  internal error text on a timeout.
- **Output encoding**: `preview` is document text rendered into the feed — it must be escaped
  on render (it is user content, and story 18 stores sanitized HTML; a preview extracted from
  HTML must not re-inject markup).

### Infrastructure Notes

- A statement timeout for the search query path is infrastructure-adjacent (DB setting or
  per-query) — it belongs in `infra/`, not hand-set on a running database.

### Integration Notes

- No external APIs in this story. «Повторить» re-enters the existing generation flow
  (`POST /generations`, story 1) and inherits its idempotency-key and polling behaviour.

---

## Hazard-Catalogue Scan Record (2026-08-01)

Group set scanned: the full `_index.md` **Groups** list at scan time — 1 money/numbers/
representation, 2 re-run safety/ordering/atomicity, 3 concurrency/consistency/distribution,
4 data lifecycle & schema, 5 request boundary & input, 6 scale & resource limits, 7 time/
operability/disclosure, 8 client/frontend. A later group addition makes this record stale
and obligates a re-scan while the spec phase is still open.

Verdicts: all 8 groups in altitude, all 8 returned GAPs. Every fired-trigger GAP is folded
into the spec as a named requirement (Acceptance Criteria / Validation Rules), except the
dismissals below.

### Seam synthesis (cross-group hazards, one named owner each)

| Seam | Groups | Guard that owns it |
|------|--------|--------------------|
| Preview truncation vs. HTML re-injection | 1 ↔ 5 | Markup is stripped to plain text **before** truncation; grapheme-boundary snap-back and render escaping asserted on the same value |
| Collation vs. pagination stability | 1 ↔ 6 | Collation pinned in the query; one mixed-script fixture asserts both the exact order and its stability across page fetches |
| NFC vs. legacy rows at rest | 1 ↔ 4 | Both sides normalized at query time (works regardless of stored form) — no back-fill dependency for search |
| Merged-read snapshot vs. legacy null link | 2 ↔ 3 ↔ 4 | Two separate guards: concurrent-conversion "exactly once", and a legacy-row back-fill/count assertion. Neither covers the other |
| «Повторить» exactly-once | 2 ↔ 3 ↔ 5 ↔ 8 | Server-side DB-backed idempotency-key exclusion under a concurrent latch — the client single-fire is explicitly **not** the guard. Owner-scoped resolution and stale-state re-check ride the same request |
| Search bound | 5 ↔ 6 ↔ 7 | Server bound is the guard: `q` length cap + statement timeout below the outer deadline + query cancellation + connection release. Debounce is not counted |
| Persisted view/sort | 3 ↔ 8 | Client-side per-device storage → no server read-modify-write; corrupt-value fallback asserted |

### Dismissed with reason

- **Money & mixed units (group 1, class 1)** — no monetary or unit-bearing quantity in the
  story.
- **Compute-then-commit ordering (group 2)** — the read path performs no writes; «Повторить»
  is a single effect.
- **Lost update (group 3)** — no cross-request read-modify-write of a domain entity; the
  persisted view/sort choice is client-side.
- **Destructive operations (group 4)** — pure read; deprecation is a contract marker only,
  and delete/rename are story 11 and drawn inert.
- **Generation-poll jitter (group 6, retry storms)** — the poll loop is story 1's contract,
  inherited unchanged; out of this story's altitude to re-guard.

---

## Additional Context

- `interview.md` — the full reasoning for the new endpoint, offset pagination, the `ILIKE`
  trade, deprecation of the old list endpoints, and what is deliberately out of scope.
- `mockups/README.md` — which frames were built from the customer screenshot vs. inferred,
  and the six recorded divergences between mockup and current code.
- Story 18 supplies the light-theme design system (`theme.css`) and the "one feed" precedent.
