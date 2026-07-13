# Decision: Register validation error taxonomy

**Date**: 2026-07-13 **Scenarios**: 1.1, 1.2, 1.3, 1.4, 1.5

Endpoints spec fixes the `{error_code, message}` envelope but not the code values, and the acceptance test for 1.1 had already locked in `INVALID_EMAIL` under strict equality — needed a taxonomy before `red-usecase` could proceed without rework.

| Rejected | Why |
|----------|-----|
| Single generic `VALIDATION_ERROR` code for all field failures | Would break the already-committed acceptance test's `INVALID_EMAIL` expectation; loses the ability for a caller to distinguish failure reason without parsing the (deliberately generic) message text |

**Chosen**: Field-scoped error codes — one constant per validation failure class (`INVALID_EMAIL`, `INVALID_PASSWORD`, `PASSWORD_MISMATCH`, ...), message stays a fixed generic string per code, never includes the submitted value.

## Model

- `backend/domain/src/shared/exceptions.py`: `ValidationException` gains an `error_code: str` field (constructor param), still a plain `DomainException` subclass — no per-field subclassing needed, callers raise `ValidationException(error_code="INVALID_EMAIL", message="...")`.
- `backend/adapters/rest/src/error_handling/exception_handlers.py`: `validation_exception_handler` maps `ValidationException` to `{"error_code": exc.error_code, "message": exc.message}` at HTTP 400, no extra fields, no stack trace.
- Email format validation lives in a domain-layer `Email` value object (new, `backend/domain/src/auth/`), fail-closed: any input not matching a bounded, non-backtracking format check is rejected (deny-by-default) rather than defaulting to valid.

## Edge Cases

| Case | Behavior |
|------|----------|
| Malformed/ambiguous email the regex can't classify cleanly | Rejected (fail-closed), not passed through as valid |
| Error message content | Never echoes the submitted raw value (avoids PII/log-injection disclosure); fixed generic string per error_code |
| Overlong or adversarial (ReDoS-shaped) email input | Length-capped before format check runs (bound enforced ahead of regex; ties to Scenario 1.2's length-limit test) |
