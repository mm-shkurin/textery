# Task 6 (bug): OAuth 5xx shows terminal error instead of retry

Type: bug

## Symptom
A backend `500` from `POST /api/v1/auth/oauth/exchange` (or `/auth/login`) lands the
user on the **terminal** OAuth error screen (or the login form-error), NOT the
retry-affording network state that scenario 4.2 requires for a server failure.

## Root cause (confirmed from the live backend contract, 2026-07-23)
The backend's generic 500 is **codeful**: `{ "error_code": "INTERNAL_ERROR", "message": … }`
(a custom app-wide handler, not FastAPI's default codeless `{detail}`). The frontend classifier
`isLoginNetworkError` (frontend/src/features/auth/utils/loginErrorHandling.ts) decides
retry-vs-terminal like this:

- no `errorCode` prop → transport failure → **network (retry)**
- has `errorCode` AND has `status >= 500` → gateway 5xx → **network (retry)**
- otherwise → **not network (terminal / form-error)**

But `toAuthApiError` attaches `status` **only on the codeless path** (the coded two-field
`{errorCode,message}` shape is a deliberate invariant guarded by the coded-error `toStrictEqual`
tests). So a codeful `INTERNAL_ERROR` 500 has an `errorCode` and **no** `status` → the classifier
returns `false` → terminal, not retry. This is the exact coded-5xx gap carried from scenario 4.2
(carryover.md), now confirmed live.

## Fix approach (design — obvious, no ADR)
Widen `isLoginNetworkError` to treat the server-fault sentinel `errorCode === 'INTERNAL_ERROR'`
as a network/retry failure. Do NOT touch the app-wide `toAuthApiError` status logic (it would break
the coded two-field invariant and its tests, and the backend won't change the shared 500 handler).
Safe for login too: login's business codes are all 4xx; a login 500 (INTERNAL_ERROR) becoming
retry-capable is an improvement over the current generic form-error.

## Scope
Frontend only: `loginErrorHandling.ts` (classifier) + a component-level pin on OAuthCallback that
a 500 routes to `/login` retry, + a regression check that email/password login's 500 goes to the
network-error state, not the field-error. No backend change.
