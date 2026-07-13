# API Conventions

Cross-cutting conventions shared by every spec in this folder. Document a convention
here once it applies to more than one endpoint — per-endpoint detail stays in that
endpoint's own `.yaml`.

## Error Envelope

Every validation failure across the REST API returns the same JSON shape at HTTP 400:

```json
{
  "error_code": "INVALID_EMAIL",
  "message": "Fixed generic string per error_code"
}
```

- `error_code` — one constant per validation-failure class (e.g. `INVALID_EMAIL`,
  `INVALID_PASSWORD`, `PASSWORD_MISMATCH`). Lets callers branch on failure reason
  without parsing message text.
- `message` — a fixed generic string per `error_code`. Never echoes the submitted raw
  value (avoids PII / log-injection disclosure).

**Implementation:** `backend/adapters/rest/src/error_handling/exception_handlers.py`
(`validation_exception_handler`) maps `ValidationException` (which carries `error_code`
as a constructor field, `backend/domain/src/shared/exceptions.py`) to this envelope for
**every** route in the app — not a per-router shadow handler. A route must let
`ValidationException` propagate uncaught rather than catching it and rebuilding the
envelope locally; duplicating the mapping in a router defeats the point of centralizing
it and risks the two copies drifting apart.

Originally introduced for the auth endpoints (see
[`stories/07-authorization/decisions/register-validation-error-taxonomy-decision.md`](../stories/07-authorization/decisions/register-validation-error-taxonomy-decision.md)),
but the handler is shared app-wide — changing its shape is a breaking change for every
existing endpoint that raises `ValidationException`, not just auth's. Any consumer
(including `frontend/src/features/generation/api/generationApi.ts`) must read
`error_code`/`message`, not the older `detail` field.
