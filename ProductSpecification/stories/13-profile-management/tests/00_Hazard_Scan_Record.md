# Hazard Scan Record — Story 13 (Profile management)

Run at `/story`, 2026-08-13, over the drafted spec. One `hazard-scan-agent` per group,
dispatched concurrently, followed by one synthesis pass over the index-named seams and every
seam an individual pass flagged.

**Group set covered (the `_index.md` Groups list at scan time): 1–8.** If a group 9 is ever
added, this spec is stale until re-scanned — per `_index.md`, "a spec whose recorded group set
is a strict subset of the current Groups list is stale".

## Verdicts

| Group | Verdict | GAPs | Covered |
|-------|---------|------|---------|
| 1 Money, numbers & representation | GAPS | 6 | 0 |
| 2 Re-run safety, ordering & atomicity | GAPS | 3 | 3 partial |
| 3 Concurrency, consistency & distribution | GAPS | 5 | 3 |
| 4 Data lifecycle & schema | GAPS | 6 | 1 |
| 5 Request boundary & input | GAPS | 5 | 0 |
| 6 Scale & resource limits | GAPS | 4 | 2 |
| 7 Time, operability & disclosure | GAPS | 4 clusters | 1 |
| 8 Client / frontend | GAPS | 6 | 4 |

**35 GAPs, all folded** into `13_ProfileManagement.md` (Validation Rules / Core Requirements)
and `13_ProfileManagement_AcceptanceCriteria.md` (named guards). **None dismissed.**

No group was out of altitude. Dismissed *sub-triggers*, with reasons, are recorded in the
individual passes: currency and arithmetic (group 1); compute-then-commit ordering and deadline
budgets, the chain being one hop deep (group 2); all async-delivery classes and read-replica
splits, no queue or replica existing (group 3); parent-child deletion and confirm-intent, this
story deleting nothing (group 4); SQL injection, SQLAlchemy parameterizing (group 5); pagination
and cursor stability, neither route paging and the migration having no backfill (group 6);
new env vars and flags, the story introducing none (group 7); optimistic render, nothing being
drawn before the server confirms (group 8).

## Seams closed in synthesis

Several GAPs were the same hazard seen from two sides. Synthesis named one guard per seam and
confirmed which side carries it, rather than letting each pass assume the other owned it.

| Seam | Passes | Single guard |
|------|--------|--------------|
| Rename rewrites status columns | 4 (blind write) + 3 (lost update) | The UPDATE sets only `name` — SQL-shape capture, plus a whole-row re-read after renaming a verified account |
| Invisible / blank name | 1 + 4 + 5 | Blankness is modelled on `required_topic()` (`generation_validation.py`) but stricter: whitespace + `Cf` + named invisible non-format code points, and `Cc`/`Cs` refused outright. Blank clears to NULL, so "no name" has one representation. Widened at `/api-spec` — the borrowed predicate let U+3164 persist as an unrenderable name and let a NUL (U+0000) reach Postgres as a 500 |
| Write actually reaches Postgres | 1 + 2 + 3 + 7 | One db test: real Postgres, separate-session re-read, INSERT and UPDATE paths, maximal-astral + NFD fixture |
| Absent vs null vs empty | 4 (data loss) + 5 (parsing) | Three presence tests, plus a request model that carries presence instead of collapsing all three to `None` |
| Identity snapshot staleness | 3 + 5 + 7 + 8 | Session-generation stamping: superseded responses dropped, snapshot updated on the write path and cleared on sign-out |
| Header degraded render | 2 + 5 + 7 + 8 | Per-state defined UI, degraded visibly distinct from loading, «Выйти» functional in every state |
| `created_at` on the wire | 1 + 4 + 7 | `Z`-suffixed UTC via the existing `_as_utc` precedent; naive input raises; client date test TZ-pinned to a non-UTC zone |
| Length unit | 1 + 8 (+ OpenAPI as a third counter) | Code points everywhere — domain, client counter, and the `maxLength` written at `/api-spec` |
| `/me` request fan-out and retries | 6 + 8 | Exactly one `GET /me` per page across two mounted menus and across in-app navigation; bounded timeout, abort on unmount, capped jittered retries |
| Error-body shape | 5 + 7 | Every failure family answers `{error_code, message}`; the over-length case reaches the domain path, not Pydantic's 422, which echoes the input back |
| Migration on a live fleet | 2 + 3 + 4 + 6 | N-1 code against N schema, plus upgrade→downgrade→upgrade preserving pre-existing rows |

## One scan finding contradicted the interview

Group 6 challenged the interview's Performance paragraph, which declined a load scenario because
the story adds no queue, no external API and no table scan. That reasoning is accurate and does
not address request rate — the binding constraint under this project's declared Throughput
profile — and this story makes `/me` the highest-rate endpoint in the product. The load scenario
is in scope; the revision is recorded in `13_ProfileManagement_AcceptanceCriteria.md` and the
Notes rather than by silently editing the interview.
