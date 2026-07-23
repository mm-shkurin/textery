# Task 6: OAuth 5xx shows terminal error instead of retry — Progress

Type: bug

## Spec
- [x] spec

## Fix: codeful INTERNAL_ERROR 5xx misclassified as terminal, not retry
- [x] root cause analysis — confirmed from the live backend contract (2026-07-23): the generic 500 is
  codeful `{error_code:"INTERNAL_ERROR", message}`; `toAuthApiError` attaches `status` only on the
  codeless path, so `isLoginNetworkError` (keyed on `status>=500`) returns false for it → terminal, not
  retry. The coded-5xx gap carried from scenario 4.2, now live. See spec.md.
- [S] design — fix approach is obvious (widen `isLoginNetworkError` to treat `errorCode==='INTERNAL_ERROR'`
  as network); no ADR. Rejected the alternative (attach status on the coded path) — it breaks the coded
  two-field invariant and its app-wide tests.
- [x] steps discovery (scope: frontend classifier util + OAuthCallback component + login regression;
  no new external seams/adapters — pure client classification change; hazard groups n/a for a frontend-only
  logic widening; GAPs: none fired — the login-regression guard below covers the shared-classifier blast radius)
- [~] red-frontend-api — classifier unit test: `isLoginNetworkError({errorCode:'INTERNAL_ERROR'})` (no status)
  → true; `{errorCode:'INTERNAL_ERROR', status:500}` → true; a 4xx business code (INVALID_CREDENTIALS) stays
  false; a bodyless transport error stays true. Predict RED on the codeful-INTERNAL_ERROR case.
- [ ] green-frontend-api — widen `isLoginNetworkError` (add the INTERNAL_ERROR sentinel branch).
- [ ] red-frontend — OAuthCallback: exchange rejects `{errorCode:'INTERNAL_ERROR', message}` (unauth) →
  navigate('/login', retry banner), NOT the terminal `oauth-callback-error`. Predict RED.
- [ ] green-frontend — verification only (the classifier fix above already resolves it); un-skip if skipped.
- [ ] red-frontend (login regression) — LoginForm: login() rejects `{errorCode:'INTERNAL_ERROR'}` → the
  distinct `login-network-error` (retry) state, NOT the field-level `login-form-error`. Predict RED.
- [ ] green-frontend (login regression) — verification only (same classifier fix).
