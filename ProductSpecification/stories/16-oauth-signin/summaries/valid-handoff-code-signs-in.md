# Scenario 3.1 — Valid handoff code signs the user in

## align-design (2026-07-22)

**Quirk:** jsdom applies no CSS, so a callback whose entire shell lives in an imported stylesheet plus classnames has NOTHING in the 318-test suite that can go RED if the `import './AuthForm.css'` line or an `auth-card`/`auth-subtitle` classname is dropped — the error state had in fact been shipping with no shared classes at all (browser-default 32px h1, unstyled copy) and no test noticed.
**Where:** frontend/src/features/auth/components/OAuthCallback.tsx + OAuthCallback.css.
**Implication:** any auth screen that reuses the shared shell needs an explicit class-contract test asserting the exact `class` attribute; CSS correctness itself stays uncovered until the backend-gated selenium pass.
