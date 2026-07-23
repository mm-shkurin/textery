# Story 16 — Carryover

Enduring quirks and decisions promoted from completed scenarios. Read on resume.

## Quirk: jsdom applies no CSS — shell reuse needs a class-contract test
**Quirk:** a callback/auth screen whose shell lives in an imported stylesheet plus classnames has nothing in the jsdom suite that can go RED if the CSS import or an `auth-card`/`auth-subtitle` classname is dropped — the OAuth error state shipped with no shared classes and no test caught it.
**Where:** frontend/src/features/auth/components/ (shared `.auth-card`/`.auth-subtitle` from AuthForm.css).
**Implication:** every screen reusing the shared shell needs an explicit test asserting the exact `class` attribute; real CSS correctness stays uncovered until the backend-gated selenium pass.
**From:** scenario 3.1 (valid-handoff-code-signs-in)
