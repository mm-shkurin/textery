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

## Request Body Cap

_Specified by story 13, not yet implemented._

Every request body is capped at **2 MiB**, refused before it is buffered and parsed. Over
the cap the answer is `413` in the envelope above, with `error_code`
`REQUEST_BODY_TOO_LARGE`.

- **Where it lives:** an ASGI middleware in the rest adapter, not a proxy directive.
  `infra/docker-compose.yml` publishes the backend port directly — the only nginx in the
  repo serves the built frontend — so there is no reverse proxy in front of the API to
  carry a `client_max_body_size`. The middleware refuses on `Content-Length` before
  reading, and aborts a chunked or length-less body once accumulated bytes cross the cap.
- **Why the middleware answers directly** instead of raising `ValidationException`: it runs
  before routing, where the app's exception handlers are not yet in play. It builds the
  same two-key body itself.
- **Where the number comes from:** the largest legitimate body in the product, which is
  `documents_save`'s 200 000 code points of content — up to ~800 KB as UTF-8 before JSON
  escaping. 2 MiB clears that with headroom and still refuses the multi-megabyte payloads
  a per-field length check cannot, because a field check only runs once the whole body is
  already in memory.

Introduced by story 13 (`stories/13-profile-management/endpoints.md`), which needs a 10 MB
`name` refused at the boundary rather than at its 256-code-point domain gate. It applies
app-wide from that point: no existing endpoint's legitimate traffic is affected, but every
one of them gains this refusal.
