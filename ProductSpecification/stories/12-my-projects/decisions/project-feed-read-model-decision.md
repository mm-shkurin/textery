# Decision: The feed is a dedicated read model, not a composition of the existing list ports

**Date**: 2026-08-02 **Scenarios**: 1.1 (first hit), binding on 1.2–1.8, 2.x, 3.x, 6.x

`total`, the offset window and the 200-code-point preview must come from one snapshot,
and no arrangement of `DocumentRepository` + `GenerationStorage` can give that.

| Rejected | Why |
|----------|-----|
| Compose in the usecase over the two existing ports | Offset-paging a merge means reading both tables whole; `total` stops being a count of what `items` was drawn from, and the preview stops being a SQL prefix, so page bytes scale with stored document size |
| A database VIEW as the projection | The view's shape is a second schema to migrate, and the per-kind sort mapping still has to be built above it — the complexity moves rather than reduces |

**Chosen**: a `ProjectFeedRepository` port returning a `ProjectPage`, implemented as one
SQLAlchemy statement — `UNION ALL` over `documents` and generations no document links to,
`owner_id` as a predicate on **both** arms, allowlisted `ORDER BY` plus a `(kind, id)`
tiebreak, `LIMIT`/`OFFSET`, and `total` from a window count in the same statement.

## Model

- domain `ProjectItem` — frozen VO: `kind`, `id`, `title`, `preview`, `document_type`,
  `status`, `retryable`, `created_at`, `updated_at`.
- domain `ProjectKind` — `document` | `generation`. The source table, never a status, so a
  row's identity cannot change when story 1 adds a generation status.
- domain `ProjectStatus` — the contract's eight values. `status` is **not** a bare `str`:
  an unconstrained field is what let the fail-closed rule be written for generations only.
- domain `ProjectPageRequest(page, limit, sort, q)` — bounds in the domain, not as
  Pydantic `Query(ge=…, le=…)`, for the reason `shared.page.PageRequest` already gives: a
  violation must surface as `{error_code, message}`. Carries that class's bool-before-int
  check, which the range check alone does not cover.
- domain `ProjectPage(items, page, limit, total)`.
- usecase `ListProjects(project_feed_repository, clock)` — one port call, no other usecase.
- port `ProjectFeedRepository.list_feed(owner_id, request) -> ProjectPage`.
- rest `project_router.py` — `GET /api/v1/projects`, `Cache-Control: no-store`.

`clock` is injected now though nothing reads it until 1.5. Deferring it would make 1.5
retrofit a port through a frozen constructor, or read system time where no test can fix it.

Offset, not keyset — `updated_at`, `title` and `document_type` are all mutable, and a
keyset anchor must be immutable. `shared.page.KeysetCursor` therefore does not apply here,
and the two paging models coexist deliberately.

## Edge Cases

| Case | Behavior |
|------|----------|
| Owner resolution yields `None` | `execute` takes a non-optional `UUID` and the port refuses `None` — never an `owner_id IS NULL` predicate serving a well-formed empty 200 |
| A document status the contract does not define | Fails closed to `unknown`, same as a generation. `ALLOWED_STATUSES = ("draft",)` today, while the contract can emit `ready` — so the document arm needs the rule as much as the generation arm |
| A grapheme straddles code point 200 of the preview | The SQL prefix is a bounded *fetch*; the grapheme-aware trim happens in the domain. SQL cuts on code points and would split the cluster |
| `title_asc` / `q` under a differing DB locale | Explicit collation named on both the `ORDER BY` and the `ILIKE` — never the ambient one |
| `documents.created_at` and `generations.created_at` differ in zone type | Rejected at the schema: a naive column on one arm sorts the merged feed wrongly by exactly the UTC offset, while every single-arm test still passes |
