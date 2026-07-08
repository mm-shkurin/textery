# Scenario 1.1: Reject request with missing topic — Journey Summary

## green-usecase (2026-07-08)

**Quirk:** `Generation._is_blank_topic()` filters ordinary whitespace (`isspace()`) and Unicode category `Cf` (format chars, e.g. U+200B), but not category `Cc` (control chars, e.g. NUL) or `Cs` (surrogates) — a topic consisting solely of those characters currently passes the guard.
**Where:** `backend/domain/src/generation/generation.py`, `_is_blank_topic()`.
**Implication:** such a topic falls through to `Generation.create()`'s `NotImplementedError` stub today; once a valid-topic path exists, it would be treated as non-blank content. Flagged independently by both pre-commit review passes on this commit; not yet closed.

## green-adapter rest (2026-07-08)

**Quirk:** `app.add_exception_handler(ValidationException, validation_exception_handler)` is registered only inside the adapter test's throwaway local `FastAPI()` instance — no shared/importable app module registers it.
**Where:** `backend/adapters/rest/tests/router/generation/test_generation_router.py`; no equivalent registration exists in `backend/adapters/rest/src/` or anywhere under `backend/application` (which doesn't exist yet).
**Implication:** the next step (`green-acceptance`) needs a real running app for the black-box test to hit, so the exception-handler registration (and the ADR's still-missing catch-all `Exception` → 500 handler) has to be replicated wherever that composition root is built — nothing in the code currently signals this is owed.
