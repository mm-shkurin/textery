## 2026-07-10 — task created and closed in one ad-hoc session

Origin: manual review request covering six independent defects across the
generation flow (provider auth fail-open, error leakage, storage race,
constant duplication, typing inconsistency, unbounded input). Task created
retroactively after the fixes were already planned and implemented via
`EnterPlanMode` — not via `/task` before coding.

Execution order was deliberately: cheap/mechanical fixes first (credentials,
sanitization, dedup, typing, length guards), optimistic locking last since
it was the highest-risk change (new column, new migration, new exception
type, storage race behavior change).

**Notable while implementing:**
- The repo had moved on since this task was scoped — `generation_storage.py`
  had gained a `list_stale()` method and `generation_model.py` an
  `index=True` on `status` (both unrelated, added independently) plus a
  migration `c3d4e5f6a7b8` chained on top of what was then the head. The new
  `version` migration (`b2c3d4e5f6a7`) had to be inserted *under* that one
  rather than at the tip — confirmed by checking `down_revision` chains and
  `alembic current` rather than assuming migration head from an earlier
  file listing.
- `backend/adapters/generation_provider` and `backend/domain` had no test
  suite/conftest at all before this task — both were scaffolded from
  scratch (sys.path wiring copied from the `adapters/rest` test conftest
  pattern) to host the new credential-check and length-guard tests.
- Optimistic locking implemented as an explicit manual version check in
  `update()` (fetch, compare, bump, commit) rather than SQLAlchemy's
  `version_id_col` mapper feature — kept consistent with the rest of the
  storage adapter's plain, hand-written style.

**Deferred / not done:** no retry-on-conflict was added for
`ConflictException` bubbling out of `GenerateDocument.execute` — it
propagates as an unhandled exception today, same as `NotFoundException`
already did. Only add retry here if a concrete concurrent-write scenario is
observed in practice; speculative retry logic wasn't requested.
