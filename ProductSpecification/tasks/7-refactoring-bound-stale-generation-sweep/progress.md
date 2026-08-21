# Task 7: Bound the stale-generation sweep query -- Progress

Type: refactoring

Origin: deferred out of Story 14 on 2026-08-19 (see `spec.md` § "Why it is not Story 14's").
Not started — this task is a parking place for a real pre-existing risk, not scheduled work.

## Spec
- [x] spec

## Fix

### Step 1: Red — the sweep reads a bounded batch
- [ ] db-adapter test: a backlog far larger than the batch size yields at most the batch size
      from one `list_stale` call, and the order is deterministic
- [ ] usecase test: successive activations drain the remainder rather than re-reading the head
- [ ] `/test-review`

### Step 2: Green — apply the limit
- [ ] named batch-size setting with a default, alongside the other sweep settings
- [ ] `list_stale(older_than, limit)` with a deterministic `ORDER BY`
- [ ] `RequeueStaleGenerations` passes it through; per-row CAS and skip behaviour unchanged
- [ ] `/test-coverage`

### Step 3: Verify against the Story 14 scenario
- [ ] promote `03_Load_Tests.md` §3.1 from `[S]` and run it: rows fetched per activation
      <= the batch size, independent of backlog depth
- [ ] `/refactor` in its own commit
- [ ] `/agent-review` + `/premortem`
