# Scenario 4.2 — Exchange network or server failure is retry-affording

## green-frontend (2026-07-23)

**Quirk:** A bare `Error` (no `errorCode` prop) is classified as a TRANSPORT/network failure by `isLoginNetworkError`, so once 4.2's `.catch` branch landed, any callback test that rejected the exchange with a bare `Error` to reach the terminal-error path instead routed to `/login`.
**Where:** frontend/src/features/auth/utils/loginErrorHandling.ts (`isLoginNetworkError` — `!hasProp(error,'errorCode') → true`), consumed by OAuthCallback `.catch`.
**Implication:** A callback test that wants the terminal `oauth-callback-error` path must reject with a BUSINESS-shaped value (`{errorCode:'INVALID_OR_EXPIRED_OAUTH_CODE', …}`), not a bare `Error` — 3.2's `exactlyOnce` double-mount error guard had to be switched to a business-shaped rejection to stop colliding with 4.2.

## red-frontend-api (2026-07-23)

**Quirk:** The exchange classifies a 5xx as retry-network ONLY when the body is codeless — `toAuthApiError` attaches `status` on the codeless path only, and `isLoginNetworkError` keys off `status>=500`; a 5xx carrying an `error_code` maps to `{errorCode,message}` with no status → classified NOT-network → terminal error, not retry.
**Where:** frontend/src/features/auth/api/apiError.ts (status attached only when `!hasUsableCode`) + loginErrorHandling.ts.
**Implication:** Whoever wires the real backend must emit 5xx as codeless (FastAPI default `{detail}` already is), OR widen `isLoginNetworkError` to treat `status>=500` as network regardless of errorCode — else a server outage strands OAuth users on the dead-end terminal screen.
