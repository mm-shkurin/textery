## green-usecase (2026-07-13)

**Decision:** Tightened the Email domain regex to reject consecutive dots and leading/trailing hyphens in a domain label (`user@example..ru`, `user@-example.com`, `user@example-.com`).
**Why:** Premortem on the first green-usecase commit flagged that the original regex accepted RFC-invalid domain syntax that would bounce at real mail servers, with zero test coverage of that gap.
**Where applied:** `backend/domain/src/auth/email.py` `_EMAIL_PATTERN`.

## adapters-discovery (2026-07-13)

**Quirk:** The existing REST exception handler (`validation_exception_handler` in `backend/adapters/rest/src/error_handling/exception_handlers.py`) maps `ValidationException` to `{"detail": str(exc)}` — not the `{"error_code", "message"}` shape this story's endpoints.md requires.
**Where:** `backend/adapters/rest/src/error_handling/exception_handlers.py`.
**Implication:** Every auth scenario that raises `ValidationException` (all of 1.1-1.5 and beyond) needs this handler remapped before its `green-acceptance` can pass — fix once at `red-adapter rest`/`green-adapter rest` for 1.1, not per-scenario.

## red-adapter rest (2026-07-13)

**Mistake:** Disabled the new rest-adapter test with a class-level `@pytest.mark.skip` while the test module imported a not-yet-existing module (`router.auth.auth_router`) at file scope.
**Why wrong:** `@pytest.mark.skip` only stops a *collected* test from running — it can't stop a `ModuleNotFoundError` raised during import, which happens before pytest evaluates the decorator. The whole `backend/adapters/rest` test module failed to collect, not just the new test (caught by agent-review, verdict BLOCK).
**Correct location/approach:** `pytest.importorskip("router.auth.auth_router", reason=...)` at module scope, then read `router`/`get_register_user_usecase` off the returned module object — defers the import so it becomes a real skip instead of a collection error.
