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

## green-adapter rest (2026-07-13)

**Quirk:** Remapping the shared `validation_exception_handler` to `{error_code, message}` is a breaking change to every existing route that relies on it, not just the new auth route — `generation_router`'s error responses changed shape too (`{"detail": ...}` → `{"error_code", "message"}`).
**Where:** `backend/adapters/rest/src/error_handling/exception_handlers.py`.
**Implication:** Callers of any `ValidationException`-raising endpoint must read the new shape. The frontend generation API client degrades gracefully via a `body?.detail ?? body?.message` fallback, but nothing pins that contract with a test — a future scenario should not assume this coupling stays safe by accident.

## green-adapter rest (2026-07-13)

**Mistake:** First implementation of the auth router caught `ValidationException` locally and rebuilt the `{error_code, message}` JSON response inline, shadowing the shared handler instead of letting the exception propagate to it.
**Why wrong:** Duplicates the exact mapping the shared handler already owns; if the two ever diverge nothing forces them back in sync, and the whole point of centralizing the handler (per the decision doc) is defeated.
**Correct location/approach:** Let `ValidationException` propagate uncaught; rely on the app-level `validation_exception_handler`, matching `generation_router`'s convention.
