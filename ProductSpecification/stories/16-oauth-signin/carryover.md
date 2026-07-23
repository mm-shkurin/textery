# Story 16 — Carryover

Enduring quirks and decisions promoted from completed scenarios. Read on resume.

## Quirk: jsdom applies no CSS — shell reuse needs a class-contract test
**Quirk:** a callback/auth screen whose shell lives in an imported stylesheet plus classnames has nothing in the jsdom suite that can go RED if the CSS import or an `auth-card`/`auth-subtitle` classname is dropped — the OAuth error state shipped with no shared classes and no test caught it.
**Where:** frontend/src/features/auth/components/ (shared `.auth-card`/`.auth-subtitle` from AuthForm.css).
**Implication:** every screen reusing the shared shell needs an explicit test asserting the exact `class` attribute; real CSS correctness stays uncovered until the backend-gated selenium pass.
**From:** scenario 3.1 (valid-handoff-code-signs-in)

## Decision: authenticated callback rejection is broad, not error-code-scoped
**Decision:** On an exchange rejection the callback redirects to the app shell whenever `isAuthenticated()` is true — any late/duplicate failure, not only an already-used code.
**Why:** Spec is deliberately broad; sessionStorage is tab-scoped so an authenticated callback means signed-in this session, and token expiry is the refresh layer's concern.
**Where applied:** OAuthCallback `.catch`, frontend/src/features/auth/components/OAuthCallback.tsx.
**From:** scenario 3.3 (late-duplicate-rejection-ignored)

## Quirk: a bare Error is a transport/network failure to isLoginNetworkError
**Quirk:** `isLoginNetworkError` returns true for any rejection lacking an `errorCode` prop, so a bare `Error` is treated as a network failure and (unauthenticated) routes the callback to `/login`, not the terminal error card.
**Where:** frontend/src/features/auth/utils/loginErrorHandling.ts, consumed by OAuthCallback `.catch`.
**Implication:** A callback test wanting the terminal `oauth-callback-error` path must reject with a business-shaped `{errorCode:…}` value, never a bare `Error`.
**From:** scenario 4.2 (network-failure-retry-affording)

## Quirk: only a codeless 5xx is retry-classified; a coded 5xx is terminal
**Quirk:** `toAuthApiError` attaches `status` only on the codeless path, and `isLoginNetworkError` keys network-ness off `status>=500`; a 5xx carrying an `error_code` has no status → classified NOT-network → terminal error, not retry.
**Where:** frontend/src/features/auth/api/apiError.ts + loginErrorHandling.ts.
**Implication:** Backend must emit 5xx as codeless (FastAPI default is), or the classifier must widen to status>=500 regardless of errorCode — else a server outage dead-ends OAuth users on the terminal screen.
**From:** scenario 4.2 (network-failure-retry-affording)

## Quirk: the coded-5xx-is-terminal rule now has an INTERNAL_ERROR exception (Task 6)
**Quirk:** `isLoginNetworkError`'s final fall-through returns `hasErrorCode(error,'INTERNAL_ERROR')`, so a status-less codeful `{errorCode:'INTERNAL_ERROR'}` (the backend's generic 500) IS retry-classified — partially superseding the carryover entry above. The widening keys on that ONE sentinel; every other coded-but-statusless business error (INVALID_CREDENTIALS, INVALID_OR_EXPIRED_OAUTH_CODE) still returns false → terminal.
**Where:** frontend/src/features/auth/utils/loginErrorHandling.ts.
**Implication:** OAuth 5xx now shows the retry banner, not the terminal card. No end-to-end test drives a real backend 500 body through `toAuthApiError` — if the live backend spells the code differently (INTERNAL_SERVER_ERROR / lowercase), the fix is a silent no-op behind a green suite.
**From:** Task 6 (oauth-5xx-terminal-not-retry)

## Quirk: MemoryRouter rerender + no-op navigate mock can't clear location.state
**Quirk:** A test that mounts under `MemoryRouter` with a mocked no-op `useNavigate` cannot make an effect's `navigate(...,{state:{}})` actually clear `location.state` — MemoryRouter ignores changed `initialEntries` on rerender, so a component reading live `location.state` and one reading a captured local copy are indistinguishable in that setup.
**Where:** frontend/src/features/auth/components/__tests__/ (OAuthErrorBanner.staleBanner vs survivesScrub).
**Implication:** To prove a component survives its own history-state scrub (capture-locally vs blank-on-scrub), the discriminating test must leave react-router REAL so the scrub genuinely mutates state; a no-op-navigate + rerender guard is non-discriminating.
**From:** scenario 4.1 (provider-error-distinct-message)
