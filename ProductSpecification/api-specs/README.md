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

## Unknown Constants

Several specs say a constant "follows the stated unknown-value policy". This is that
statement; it applies to every enum in this folder.

- **Reading a stored value the code does not define is a clean failure, not a coercion.**
  A `status`, `source` or event `type` column holding an unrecognised value makes the read
  fail loudly (500 with the generic envelope, and an attributable log record). It is never
  silently mapped to the first constant, and it never crashes a stream mid-frame.
  Rationale: an unrecognised stored state means the row was written by code with a
  different idea of the state machine — guessing which constant it "probably" meant is how
  a cancelled edit becomes a completed one.
- **Reading an unrecognised value off the wire is tolerated by the client.** An SSE event
  whose `event:` type the client does not know is ignored, and the stream continues. An
  unrecognised *terminal* kind is treated as `error` — unfreeze and offer retry — never as
  success.
- **Unknown fields in a request body are ignored, not rejected**, so a newer client can add
  one without a coordinated deploy. This is distinct from server-owned fields, which are
  also ignored but for a different reason (see the mass-assignment notes per endpoint).

## Keyset Cursors

`cursor` on every paginated endpoint is opaque and server-generated.

- absent, or present-but-empty → the first page (empty is the same as absent: a client
  building a query string from an empty variable must not get a 400 for it)
- structurally invalid, or valid-looking but not one this server issued → **400**
- referring to a resource the caller does not own → **404**, matching the endpoint's own
  not-found rule rather than confirming the resource exists

