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

Every request body is capped at **2 MiB** in the application, refused before it is buffered
and parsed. Over the cap the answer is `413` carrying the same two keys as the envelope
above, with `error_code` `REQUEST_BODY_TOO_LARGE`.

**There are two enforcement points, and they must be set in this order.** A browser does
not reach the app directly: `infra/docker/nginx/frontend.conf` proxies `location /api/` to
`backend:8000`, so the built SPA calls the API same-origin, and its own comment names a
further host/prod-copy reverse proxy in front of that container. Acceptance tests, by
contrast, hit `BACKEND_PORT` directly (`acceptance/clients/application/application_client.py`).
So:

- **nginx (`client_max_body_size`) — the outer backstop, set ABOVE the app cap** (4 MiB).
  It is currently unset, which means nginx's default of **1 MiB** is the real ceiling on
  every browser request today, and nginx answers it with its own HTML error page, not with
  `{error_code, message}`. Setting it below or equal to the app cap makes the canonical
  413 unreachable for real users while acceptance tests — which bypass nginx — still see
  it. Above the app cap, the app answers every realistic over-cap body and nginx only
  catches the absurd ones.
- **The ASGI middleware in the rest adapter (2 MiB) — the one that produces the contract.**
  It refuses on `Content-Length` before reading, and aborts a chunked or length-less body
  once accumulated bytes cross the cap. It answers directly rather than raising
  `ValidationException`, because it runs before routing, where the app's exception handlers
  are not yet in play — it builds the same two-key body itself. For that reason
  `REQUEST_BODY_TOO_LARGE` is deliberately **absent** from `_ERROR_CODE_STATUS_MAP`: adding
  it there would not route this response, and would silently turn any later
  `ValidationException` of that code into a 400.
- **A body between 2 and 4 MiB still answers the canonical 413; above 4 MiB a browser gets
  nginx's HTML.** Named as an accepted residual rather than discovered later: no legitimate
  client produces one.

**Where the app number comes from:** the largest legitimate body in the product, which is
`documents_save`'s 200 000 code points of content — up to ~800 KB as UTF-8 before JSON
escaping. Note what that means for today's unset nginx directive: a maximal legitimate
document save already sits at roughly 80% of the 1 MiB default, so the missing directive is
a live near-miss on `PUT /api/v1/documents/{id}`, not only a story-13 concern.

Introduced by story 13 (`stories/13-profile-management/endpoints.md`), which needs a 10 MB
`name` refused at the boundary rather than at its 256-code-point domain gate — a per-field
length check only runs once the whole body is already in memory. It applies app-wide from
that point: no existing endpoint's legitimate traffic is affected, but every one of them
gains this refusal.

**Guard.** The 413 body must be asserted through the **frontend origin** (`app_url` in
`acceptance/conftest.py`), not only through `BACKEND_PORT` — an assertion made only against
the backend port is green on a path no user takes. `frontend/scripts/check-nginx-503.mjs`
already scans that conf in CI for 503-producing directives and is the natural place to also
pin `client_max_body_size` ≥ the app cap.
