# Scenario 3.3 — A late duplicate rejection after a stored success is ignored

## green-frontend (2026-07-23)

**Decision:** On an exchange rejection the callback treats ANY late/duplicate failure as benign when `isAuthenticated()` is true (redirect to the app shell) — the redirect is NOT scoped to an already-used/duplicate error code.
**Why:** The spec is deliberately broad (16_OAuthSignin.md:49-50 / Notes:48-50 — "any late/duplicate rejection after a stored session is ignored"), and tokens live in sessionStorage (tab-scoped), so `isAuthenticated()` true at the callback means signed-in this tab session; an expired access token is the app refresh layer's concern, not the callback's. A premortem asked to scope to the error code — declined for these reasons.
**Where applied:** OAuthCallback `.catch` (`isAuthenticated()` branch), frontend/src/features/auth/components/OAuthCallback.tsx.
