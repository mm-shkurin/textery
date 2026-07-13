## green-usecase (2026-07-13)

**Decision:** Tightened the Email domain regex to reject consecutive dots and leading/trailing hyphens in a domain label (`user@example..ru`, `user@-example.com`, `user@example-.com`).
**Why:** Premortem on the first green-usecase commit flagged that the original regex accepted RFC-invalid domain syntax that would bounce at real mail servers, with zero test coverage of that gap.
**Where applied:** `backend/domain/src/auth/email.py` `_EMAIL_PATTERN`.

## adapters-discovery (2026-07-13)

**Quirk:** The existing REST exception handler (`validation_exception_handler` in `backend/adapters/rest/src/error_handling/exception_handlers.py`) maps `ValidationException` to `{"detail": str(exc)}` — not the `{"error_code", "message"}` shape this story's endpoints.md requires.
**Where:** `backend/adapters/rest/src/error_handling/exception_handlers.py`.
**Implication:** Every auth scenario that raises `ValidationException` (all of 1.1-1.5 and beyond) needs this handler remapped before its `green-acceptance` can pass — fix once at `red-adapter rest`/`green-adapter rest` for 1.1, not per-scenario.
