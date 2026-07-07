# Decision: Request Validation Architecture (domain-level, centrally mapped)

**Date**: 2026-07-07 **Scenarios**: 1.1, 1.2, 1.3, 1.4 (and the same shape in stories #2-4)

Needed one enforcement point for all `POST /generations` field validation before scenario
1.1's `red-usecase`, since a per-controller imperative check would fragment the same
guards (trim/length/tri-state emptiness) across every field and every future scenario.

| Rejected | Why |
|----------|-----|
| Controller-level imperative check (`if not request.topic: raise HTTPException(...)`) | Duplicates trim/length/omit-null-empty logic per field as 1.2/1.3 land; still needs a separate centralized catch-all handler anyway; risks an inconsistent enforcement architecture vs. 1.4's `document_type` check (422). |

**Chosen**: `Generation.create(...)` domain factory validates all fields and raises
`ValidationException`; composition root registers two centralized FastAPI exception
handlers — `ValidationException` → 400, catch-all `Exception` → generic 500 (never
echoes internals).

## Model

- `Generation.create(topic, volume_pages, requirements, extra_wishes, document_type)` —
  domain factory, sole entry point for field validation.
- `ValidationException` — existing domain exception (per `coding.md`), raised by the
  factory.
- Two exception handlers registered once in `backend/application`'s composition root.

## Edge Cases

| Case | Behavior |
|------|----------|
| `topic` omitted / `null` / `""` / whitespace-only / invisible-char-only | All rejected identically — factory trims before checking non-empty. |
| `topic` over max length (300 chars) | Rejected with a distinct message, same `ValidationException` → 400 path. |
| Any unhandled exception (bug, not a validation failure) | Caught by the generic handler → 500, body never contains `str(exception)` or a traceback. |
