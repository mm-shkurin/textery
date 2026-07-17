# Task 4: Generations auth -- Progress

Type: bug

## Spec
- [x] spec

## Fix: /api/v1/generations accepts anonymous callers and records no owner

Executed **off-framework** on 2026-07-17, at the user's explicit direction: the hole was
live and the full sequence (~19 commits across discovery + per-layer red/green +
test-review + coverage + refactor + review passes) was judged too slow against it. The
discovery steps below are marked `[S]`, not `[x]` — they did not run, and recording them
as done would misrepresent what was verified.

- [S] root cause analysis — skipped as a `/rca` step. The cause was read directly from the
      code and is recorded in `spec.md` under Root Cause; it is structural (no owner column
      exists anywhere in the slice), so there were no competing hypotheses to test.
- [S] design — skipped as a `/design-preview` step. The approach mirrors the already-shipped
      documents slice and its ADR
      (`stories/05-manual-mode/decisions/document-ownership-decision.md`) rather than
      deciding anything new. The two decisions that WERE open were settled by the user on
      2026-07-17: work lands on `feature/05-manual-mode-backend` (the only branch carrying
      `get_current_owner_id`), and existing rows are deleted in the migration on all
      environments.
- [S] steps discovery — skipped as a gate, **including its hazard-catalogue fan-out**. This
      is the one skip with real residual risk: that gate exists to catch a fix that guards
      one direction of a hazard and leaves its twin open, and nothing systematically checked
      for twins here. One was found by hand (the BackgroundTasks re-read, closed by
      threading the owner through), but "found one by hand" is not the same as "scanned".
- [x] fix — migration (DELETE + `owner_id NOT NULL` FK/index), owner on `Generation` and
      `GenerationModel`, `get_by_id_and_owner` replacing the unguarded `get(id)` on the port
      and adapter, owner threaded through `RequestGeneration` / `GetGeneration` /
      `GenerateDocument` / `RequeueStaleGenerations` / container, `Depends(get_current_owner_id)`
      on both endpoints, api-specs updated.
- [x] verified — `pytest backend/` 304 passed / 0 failed. Migration proven by round-trip:
      downgraded, seeded a legacy ownerless row, upgraded — row deleted, column lands
      `uuid NOT NULL` with FK + index. The reported curls re-run against the real
      composition root in-process (fake provider, no GigaChat spend): anonymous POST 401,
      `Bearer garbage` 401, real token 201, own GET 200, anonymous GET 401, another
      account's generation 404.

## Not done — deliberate, and live

- **No acceptance-level test.** The end-to-end probe above was a throwaway script, not a
  committed test. The suite proves the guard at the unit/adapter level; nothing in CI drives
  the real composition root end to end for generations. A regression that unwired
  `Depends(get_current_owner_id)` in `main.py`'s override table would keep every test green.
- **No hazard scan.** See the `[S]` above.
- **`Idempotency-Key` on generations is spec-only.** `generations_create.yaml` declares the
  header required and 200-on-replay; the router reads no such header and no route implements
  it. Pre-existing drift, untouched here — flagged because the spec now reads as if it were
  the shipped contract.
- **404 body shape is inconsistent.** `GET /generations/{id}` answers `{"detail": ...}` via
  `HTTPException`, while documents answer the project's `{error_code, message}` envelope.
  Pre-existing; changing it is a frontend-visible contract change and was out of scope.
