# Task 1: Generation error-handling hardening

Type: refactoring

## Solution

Triggered by a backend-only automated quality audit (score 2.5/3.0) that flagged
silent failure paths in the generation flow:

1. `GenerateDocument.execute` retries the generation provider once (max 2
   attempts) instead of failing on the first transient error, and logs each
   failed attempt plus the final exhausted failure.
2. `unhandled_exception_handler` logs the request method/path and traceback
   (`exc_info`) before returning the generic 500, instead of swallowing the
   exception silently.

Two audit findings were considered and deliberately **not** applied:
- Wrapping `httpx` calls in `GigaChatProvider` with try/except — redundant,
  `GenerateDocument.execute` already catches `Exception` around
  `provider.generate()`.
- Adding Pydantic `Field(ge=1, le=10)` to `volume_pages` in
  `GenerationRequestDto` — would duplicate the domain's own range validation
  in `Generation.create` and diverge the error contract (422 vs. the existing
  400 `ValidationException` path exercised by scenario 1.2).

## Key Files

- backend/usecase/src/generation/generate_document.py
- backend/usecase/tests/fake/generation/fake_generation_provider.py
- backend/usecase/tests/statements/generation_lifecycle_statements.py
- backend/usecase/tests/generation/test_generation_lifecycle_usecase.py
- backend/adapters/rest/src/error_handling/exception_handlers.py
- backend/adapters/rest/tests/error_handling/test_exception_handlers.py
