# Story 7: Authorization — Progress

Owns the story-level narrative, decisions, and the Spec checklist — shared context that
doesn't belong to one layer. `progress-backend.md` (Backend + Integration + Security +
Load + Infrastructure Scenarios) and `progress-frontend.md` (Frontend Scenarios, not yet
created — start it when frontend work begins) own the per-scenario checklists.
`ProductSpecification/stories.md` is the cross-file rollup.

## Spec Checklist

- [x] interview — `interview.md`
- [x] story — `07_Authorization.md`, `07_Authorization_Notes.md`
- [x] mockups — `mockups/` (5 screens × desktop/mobile, screenshots taken)
- [x] api-spec — `endpoints.md`, `ProductSpecification/api-specs/auth_*.yaml`
- [x] test-spec — `tests/` (main + extended), hazard-catalogue scan folded in

## Key Decisions

- Scope is email+password only this iteration — Yandex ID / VK ID OAuth explicitly
  deferred (see `interview.md` Scope).
- Design diverges from the Figma mockups' actual flow (email+OTP passwordless as
  primary, password as secondary) — user explicitly chose to keep email+password at
  registration per the original spec; Figma was used only for visual style/copy
  reference in the mockups, not for the flow itself.
- Verification code returned directly in the register/resend API response (mocked, no
  real email) — accepted resend/verify credential-disclosure trade-off, documented in
  `07_Authorization_Notes.md` Security Considerations and tested in
  `tests/05_Security_Tests.md` #10.
- 16 hazard-catalogue GAPs found across story-spec and test-spec scans (both phases) —
  all folded into named requirements/scenarios rather than dismissed; see
  `07_Authorization.md`/`07_Authorization_Notes.md` and `tests/01_API_Tests.md` §2.4a-d,
  §3.6, §5.5a, §5.6a, §5.7, §6.1a, §6.4, §6.5 for the backend-relevant ones.

## Backend Work

Branch `feature/story-7-authorization-backend`, branched from `dev` 2026-07-13.
Per-scenario checklist in `progress-backend.md`.
