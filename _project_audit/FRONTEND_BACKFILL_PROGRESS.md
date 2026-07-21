# Frontend Backfill — Progress Log

Session rollup for the frontend arm of `FRAMEWORK_BACKFILL_PLAN.md`. Written 2026-07-21;
work done 2026-07-20 on branch `backfill/frontend`. Per-step state stays authoritative in
`ProductSpecification/stories/*/progress-frontend.md`; this file is the narrative index.

Scope boundary: this session touched only `frontend/`, `acceptance/tests/frontend/`,
`acceptance/statements/frontend/`, and the frontend layer of the story progress files.
Backend runs in a parallel session — untouched here.

## 1. Phase B — stale-skip reconcile + systemic auth-gate fix

### 1.1 Manual-editor stale Selenium skip (`f5e673e`)
- `test_manual_editor_acceptance.py` carried a **false** skip reason (`.me-content-area`
  "static placeholder div, no contenteditable"). False since the Tiptap rewrite — the child
  is a real ProseMirror contenteditable (`data-testid="editor-content-area"`).
- Fixed the Statements locator (`EDITABLE_CONTENT`), dropped dead `CONTENT_AREA`.
- Un-skipping exposed a **deeper true blocker**: Story-7 auth gate (see 1.2). Re-skipped at
  module level with an accurate dated reason.

### 1.2 Systemic auth-gate regression (`97d8b65`)
- **Finding:** Story 7 (auth, 2026-07-16) gated the type → mode → editor/workspace flow
  behind a session; an unauthenticated CTA routes to `/register`. This **silently broke every
  frontend acceptance test that navigates via the CTA** — `mode_modal` (Story 5 sc. 1.1) and
  `chat_workspace` (Story 1 sc. 4.1) were marked `[x]` green-selenium but timed out on the CTA
  click (verified failing live).
- **Fix:** a logged-in precondition (seeded `sessionStorage` session) in the shared
  `navigate_to_doklad_type_modal`. Honest for no-API screens (modals, workspace initial state)
  — both re-verified **green live**. The manual editor stays skipped: its `createDocument`
  mount call 401s a seeded token → `clearSession` → collapse to landing → needs a real backend
  session.
- **File-size:** extracted `FormAssertionsMixin` (`frontend_form_assertions.py`) so
  `base_frontend_statements.py` dropped from 242 → 132 lines (was already over the 200 cap).
- Quirk recorded in the scenario-3.1 journey summary (`c8dbd8c`).

### 1.3 Known-debt #12 (landing hero-subheading)
- Verified already clean in the tree — no subheading assertion anywhere; landing 1.1 green
  live. No action needed.

## 2. Phase C — Story 7 frontend scenarios (via `/continue`)

Backend now exists (curl-verified), so component-layer steps build without it; the
`green-selenium`/`demo`/`red-selenium` legs are **batched** as `[S]` deferred to a single
full-stack selenium pass (user-confirmed decision).

### 2.1 Scenario 5.2 — generic invalid-credentials (`e3035f3`)
- `align-design` verify-only (login error reuses the accepted inline `.auth-form-error`
  pattern). Deferred the backend-gated selenium legs.

### 2.2 Scenario 5.3 — unverified-account error — CLOSED
- `red-frontend` characterization (`05a354e`): `applyLoginError` UNVERIFIED branch already
  existed; test pins the form-level render. Predicted/Actual PASS.
- `green-frontend` (`bb7c1e2`): no prod change; hardened the test to `findByRole('alert')`
  (pins the SR announcement) + testid, dropped a tautological negative — closes the red-commit
  review findings.
- api-layer `[S]` (already covered by `loginApi.test.ts`), `align-design` verify-only
  (`8803be5`).
- Carried follow-up (`71f7da3`): the `role="alert"` region is conditionally mounted with text
  in place — jsdom `findByRole` can't verify real AT announcement; deferred to the selenium
  a11y guard.

### 2.3 Scenario 5.4 — account-locked screen — CLOSED (full net-new TDD cycle)
- **Design decision (user-confirmed):** lockout = `error_code ACCOUNT_LOCKED` + HTTP
  `Retry-After` header (seconds). **Cross-layer note for the backend session:** the login
  lockout response must emit `Retry-After` (integer seconds) and `error_code "ACCOUNT_LOCKED"`.
- `red-frontend` real RED (`c064332`) → `green-frontend` (`3df70b5`): new
  `AccountLockedScreen.tsx` (mount-once interval, `formatMmSs`, expiry→restore form,
  `clearInterval` cleanup, missing/0 → 300s fallback). Extracted `loginErrorHandling.ts` to
  keep `LoginForm.tsx` at 152 lines. All 3 red-commit review guards implemented + green.
- `refactor` (`ed172fa`): extracted `hasProp` type-guard.
- `red-frontend-api` real RED (`61bebd9`) → `green-frontend-api` (`3aa7672`): `httpClient`
  parses `Retry-After` (finite-or-omitted, never NaN) → `HttpError`; `toAuthApiError` threads
  `retryAfterSeconds` through. Header-driven (not code-driven), auth-wide scope. 3 review
  guards green.
- `align-design` (`2c223ce`): `AccountLockedScreen` aligned to mockup `04` (scoped vertical
  rhythm; reuses shared `.auth-card` 420px). design-review PASS.
- Carried follow-ups (`75df668`, `c6885e3`, `6adea3c`, `1a31186`): countdown edges, a11y
  announce, countdown drift (tick-counted vs deadline), `Retry-After: 0` fail-safe.

## 3. State at session end

- **Full frontend unit suite:** 241 passed / 0 failed; oxlint clean; `tsc -b --noEmit` exit 0.
- **Frontend acceptance (live, frontend-only stack):** landing 1.1, mode_modal, chat_workspace
  green; manual_editor honestly skipped (needs real backend session). 3 auth in-flight/loading
  tests fail frontend-only by design (need a live pending request).
- **Story 7 frontend closed this session:** 5.2 (align), **5.3**, **5.4**.
- **All new source files < 200 lines.**

## 4. Remaining frontend work

Reachable now (component-layer, backend runs in parallel):
- **Story 7:** 5.5 (wrong-code verify), 5.6 (network/timeout), 5.7 (verify refresh no-resend),
  5.8 (restore registration input), 6.3 (resend after cooldown), 6.4 (verify → app shell),
  6.5 (back-to-login from locked).
- **Story 1:** 5.1, 6.1, 6.2, 7.1, 7.2, 8.1–8.3, 9.1, 9.2, 10.1 (form/generation states).
- **Story 5:** 7.9 (Tiptap link toolbar — pure frontend); Defect NEW-1 (create 422s — likely
  a contract mismatch, may need backend coordination).

Blocked on a live backend + Postgres (cross-session, infra-guardrailed) — batched:
- All `green-selenium`/`demo`/`red-selenium` legs across Story 7 (and the manual-editor
  module). Need the full stack; Story 7 also needs the backend to emit the `Retry-After` header
  and `ACCOUNT_LOCKED` code decided in 2.3.
- The a11y-announcement, countdown-drift, and `Retry-After:0` guards recorded on 5.3/5.4's
  deferred selenium steps.

Consciously left `[S]` (unit-covered, honest reasons, no false `[x]`): Story-1 modals 1.2–3.2.

## 5. Commit index (18, oldest → newest)

```
f5e673e test: reconcile stale manual-editor Selenium skip, fix contenteditable locator
97d8b65 test: unbreak CTA-flow frontend acceptance behind Story 7 auth gate
c8dbd8c docs: record Story 7 auth-gate quirk in scenario 3.1 journey summary
e3035f3 test: align-design 5.2 (verify-only) + defer backend-gated selenium
05a354e test: red-frontend 5.3 unverified-account error (characterization)
bb7c1e2 test: green-frontend 5.3 — harden UNVERIFIED guard (role=alert), no prod change
71f7da3 docs: carry premortem a11y-announcement follow-up to 5.3 deferred selenium
8803be5 test: close 5.3 api-layer (already covered) + align-design verify-only
c064332 test: red-frontend 5.4 account-locked screen (real RED)
75df668 docs: carry 5.4 countdown-edge guards to green
3df70b5 feat: green-frontend 5.4 account-locked screen with countdown
ed172fa refactor: extract hasProp type-guard in loginErrorHandling
c6885e3 docs: carry 5.4 green premortem follow-ups (a11y announce, countdown drift)
61bebd9 test: red-frontend-api 5.4 surface Retry-After as retryAfterSeconds (real RED)
6adea3c docs: carry 5.4 red-api review guards to green-frontend-api
3aa7672 feat: green-frontend-api 5.4 surface Retry-After as retryAfterSeconds
1a31186 docs: note Retry-After:0 fail-safe edge
2c223ce style: align-design 5.4 account-locked screen to mockup 04
```
