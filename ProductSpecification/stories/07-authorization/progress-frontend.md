# Story 7: Authorization — Frontend Progress

Demo step skipped for all scenarios (visual-only, non-gating), same convention as story 1
(see `ProductSpecification/stories/01-auto-generate-doklad/progress.md`, commit `1cf7a27`).

Register/login footer cross-links use react-router-dom `Link` (not raw `<a href>`) — fixed
proactively during 1.2's align-design after agent-review/premortem flagged the pattern
twice (full-page-reload risk, route-string drift). Scenarios 6.1/6.2 will add navigation
click-through tests but the components themselves already use the router primitive.

## Frontend Scenarios (tests/02_UI_Tests.md)

### 1.1: Registration form displays email, password, confirm password fields
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api (no API call in this scenario — page-display only, per tests/02_UI_Tests.md §1 note "Start with page display (no API needed)")
- [S] green-frontend-api (see above)
- [x] align-design
- [S] green-selenium (first attempt BLOCKED — no router/no /register route in frontend/src/App.tsx; superseded by the routing sub-cycle below, see the second green-selenium entry which is the real completion)
- [x] red-frontend (routing: install router, wire /register route to render RegisterForm)
- [x] green-frontend (routing: minimal App.tsx wiring so /register renders RegisterForm)
- [x] green-selenium (retry after routing lands)
- [S] demo (skipped per convention, see note above)

### 1.2: Login form displays email and password fields — CLOSED

RESOLVED (was "Known gaps" from premortem on `fef125a`, closed further per premortem on
`7719c24`): LoginForm.tsx (green-frontend, `f2a0f88`) fixed `htmlFor`/label association
and `autoComplete` attributes; `LoginForm.test.tsx` now asserts `getByLabelText` ties to
the same elements as the testids. Enter-to-submit is native `<form onSubmit>` browser
behavior that jsdom does not simulate (verified: a `fireEvent.keyDown` unit test does not
trigger submit in jsdom) — that behavior is covered by the Selenium acceptance layer
(real browser), not a unit test; no unit-level guard is possible or needed here.
RegisterForm.tsx still lacks `autoComplete`/explicit `getByLabelText` coverage (label
association itself is present via `htmlFor`) — untouched, not part of this scenario.

- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api (no API call in this scenario — page-display only, per tests/02_UI_Tests.md §1 note)
- [S] green-frontend-api (see above)
- [x] align-design
- [S] green-selenium (BLOCKED: no /login route in App.tsx, same gap class as Scenario 1.1's /register — green-agent stopped before touching anything, skip marker untouched; superseded by routing sub-cycle below)
- [x] red-frontend (routing: wire /login route to render LoginForm)
- [x] green-frontend (routing: minimal App.tsx wiring so /login renders LoginForm; also closed premortem gap from prior step by adding a catch-all regression guard test)
- [x] green-selenium (retry after routing lands)
- [S] demo (skipped per convention, see note above)

### 1.3: Verification-code screen displays a 6-digit input and resend action

SPEC GAP (premortem on `bfa2c52`, not code defects — no scenario anywhere in
tests/02_UI_Tests.md covers these; flagged for test-spec review, not silently fixed here):
- countdown display tick-down over time is never asserted by any scheduled scenario
  (1.3/2.2/5.7/6.3 checked) — a static hardcoded "01:00" string would pass every planned
  test
- full 6-digit code paste into the box layout is not covered by any scheduled scenario —
  current per-box `maxLength=1` contract will silently truncate a paste unless split-on-
  paste logic is added, and nothing requires that logic to exist

green-frontend-api (`resendCode` wired, in-flight disable guard, swallow-only error catch)
closed 2 of the 3 premortem follow-ups from red-frontend-api. Deferred: countdown-gated
disable (`disabled={countdownSeconds > 0}`) — component has no ticking timer yet
(`countdownSeconds` is static), so gating on it now would permanently disable the button;
real fix needs a timer implementation, tracked for Scenario 2.2/5.7/6.3 (countdown-related
scenarios) or a dedicated follow-up, not scope-crept into this step.

- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [x] red-frontend-api
- [x] green-frontend-api
- [S] red-frontend (coverage: handleResend no-ops when email prop is missing) — guard clause `if (!email) return` already implemented in VerifyCodeForm.tsx (scenario 1.3 original green phase); coverage-agent's flagged gap was a false positive, confirmed via a throwaway test that passed on first run with zero production changes
- [S] green-frontend (coverage: handleResend no-ops when email prop is missing) — see red step, nothing to implement
- [S] red-frontend-api (coverage: resendCode throws on non-ok HTTP response) — resendCode already throws descriptive error on non-ok HTTP response (authApi.ts:17-18), implemented in original green-frontend-api step for scenario 1.3
- [S] green-frontend-api (coverage: resendCode throws on non-ok HTTP response) — see red step, nothing to implement
- [x] align-design
- [S] green-selenium (BLOCKED: no /verify route in App.tsx, same gap class as Scenarios 1.1/1.2 — green-agent stopped before touching anything, skip marker restored; superseded by routing sub-cycle below)
- [x] red-frontend (routing: install/wire /verify route to render VerifyCodeForm)
- [x] green-frontend (routing: minimal App.tsx wiring so /verify renders VerifyCodeForm)
- [x] green-selenium (retry after routing lands)
- [S] demo (skipped per convention, see note above)

### 2.1: Password field visibility toggle
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api (no API call in this scenario — client-side visibility toggle only, per tests/02_UI_Tests.md §2.1)
- [S] green-frontend-api (see above)
- [x] align-design
- [x] red-frontend (coverage: toggle button aria-pressed reflects show/hide state) — flagged during align-design's test-coverage pass, `aria-pressed={showPassword}` added but unasserted; new assertion added to LoginForm.test.tsx (predicted PASS, no production change needed — attribute already wired in align-design commit `96fbf68`)
- [S] green-frontend (coverage: toggle button aria-pressed reflects show/hide state) — see red step, nothing to implement
- [x] green-selenium
- [S] demo (skipped per convention, see note above)

### 2.2: Verification code input advances focus per digit
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api (no API call in this scenario — client-side focus-advance only, per tests/02_UI_Tests.md §2.2)
- [S] green-frontend-api (see above)
- [x] align-design (no styling changes needed — CSS already aligned to mockup from Scenario 1.3; design-review PASS, no hardcoded placeholder data; test-coverage focus found no genuinely new in-scope gaps)
- [x] green-selenium (test already had no skip marker from red-selenium; GREEN confirmed after resetting a stale local Postgres migration-state mismatch — infra fix, not code)
- [S] demo (skipped per convention, see note above)

### 2.3: In-flight submit buttons are disabled to prevent duplicate submission
- [x] red-selenium
- [x] red-frontend
- [x] green-frontend
- [S] red-frontend-api (no real API call in this scenario yet — placeholder Promise.resolve() boundary only; actual registration API lands in Scenario 3.1)
- [S] green-frontend-api (see above)
- [x] align-design (added .auth-submit:disabled style — opacity 0.6/cursor default, matching the existing verify-resend button convention; mockup has no explicit disabled state to match against. Only RegisterForm currently wires disabled={isSubmitting}, so this rule is only live there today — LoginForm has no in-flight state yet (Scenario 2.3a) and VerifyCodeForm has no .auth-submit button. design-review PASS, test-coverage focus found no new in-scope gaps)
- [x] green-selenium (first attempt FAILED — placeholder `Promise.resolve()` resolved before Selenium could observe the disabled window, confirming the agent-review/premortem concern from green-frontend; fixed by replacing it with a real 500ms `setTimeout` delay so the disabled state is genuinely observable. The spec's "second click doesn't trigger a duplicate request" clause was descoped from this test — untestable with zero real network requests until the registration API is wired in Scenario 3.1, see test docstring)
- [S] demo (skipped per convention, see note above)

### 2.3a: Verify, resend, and login buttons are also disabled while in flight

Three sub-cases in different states going in: **resend** already has `disabled={isResending}` +
try/finally reset wired since Scenario 1.3 (marked `[S]` below, no new test needed). **login**
has a submit button with no in-flight state — red-selenium test written and RED-confirmed.
**confirm** has no button at all on VerifyCodeForm.tsx yet (mockup `02-verify-code.html` has a
"Подтвердить" btn-primary never implemented) — red-selenium can't target a nonexistent element,
so its red-frontend step must add the button first.

- [x] red-selenium (login sub-case: test_login_submit_disabled_while_in_flight_acceptance.py, RED confirmed — `AssertionError: expected submit button to be disabled`)
- [S] red-selenium (resend sub-case) — already implemented in Scenario 1.3, disabled={isResending} + try/finally reset already exist and are already covered by VerifyCodeForm.test.tsx; no new test needed
- [x] red-frontend (login: unit test covers both disable-on-click and re-enable-after-settle, per the premortem gap on fae4969; RED confirmed — AssertionError, submit button not disabled)
- [x] green-frontend (login)
- [S] red-frontend-api (login) — no real login API call exists yet, same scoping decision as Scenario 2.3's register test; deferred until a real endpoint lands
- [S] green-frontend-api (login) — see above
- [x] red-frontend (confirm: unit test asserts a verify-confirm-button exists and disables on click; RED confirmed — TestingLibraryElementError, element not found, since the button doesn't exist yet)
- [x] green-frontend (confirm: add the Confirm button + wire useSubmitPlaceholder)
- [S] red-frontend-api (confirm) — no real verify-confirm API call exists yet, same scoping decision as login/register
- [S] green-frontend-api (confirm) — see above
- [x] red-selenium (confirm: test_verify_confirm_disabled_while_in_flight_acceptance.py — since green-frontend (confirm) already wired useSubmitPlaceholder with a genuine 500ms delay, predicted and confirmed PASS on first run, no RED state; not marked skip)
- [S] green-selenium (confirm) — test already passes, see red-selenium note above
- [S] red-frontend-api (resend, already implemented in Scenario 1.3)
- [S] green-frontend-api (resend, already implemented in Scenario 1.3)
- [x] align-design (no styling changes needed — .auth-submit:disabled CSS and mockup colors/padding already shared via the AuthSubmitButton extraction from the prior refactor commit; both LoginForm and VerifyCodeForm's Confirm button inherit it. design-review PASS (no hardcoded placeholder data), test-coverage focus found no new in-scope gaps)
- [x] green-selenium (login) — no backend needed (same as confirm sub-case: pure client-side placeholder via useSubmitPlaceholder's real setTimeout, no API call yet). Earlier attempt wrongly assumed a backend dependency and chased a stale-migration red herring on the shared Postgres volume; unskipped and reran against the frontend container alone — PASSED (1 passed in 4.20s), no production changes.
- [S] demo (skipped per convention, see note above)

### 3.1: Registration submission shows a loading state
- [x] red-selenium (test_register_submit_loading_indicator_acceptance.py, RED confirmed — TimeoutException, no `[data-testid='register-loading-indicator']` element rendered)
- [x] red-frontend (RegisterForm.test.tsx "shows a loading indicator while submitting and not before"; RED confirmed live, un-skipped by test-review since a RED test must actually run and fail — TestingLibraryElementError, no register-loading-indicator element)
- [x] green-frontend (added `data-testid="register-loading-indicator"` element rendered while `isSubmitting`, mirroring the login flow's placeholder pattern. 3 passed)
- [S] red-frontend-api — no real register API call exists yet, same scoping decision as Scenario 2.3's register test and login/confirm (line 129/133): loading state is a pure client-side placeholder via useSubmitPlaceholder, no endpoint to test against
- [S] green-frontend-api — see above
- [x] align-design (mockup has no loading-state styling — new element was previously unstyled, defaulting to black text on dark card, invisible. Added shared `.auth-loading-indicator` class in AuthForm.css (14px, #9a9ba3, centered) so it reads like other muted auth-form text. design-review PASS (no hardcoded placeholder data), test-coverage focus PASS (100% on touched lines, no gaps))
- [ ] green-selenium (docker build blocker fixed 2026-07-15 and retested — but Scenario 5.1's green-frontend replaced RegisterForm's useSubmitPlaceholder with a real registerApi.register call, so this scenario is no longer client-side-only. Backend has no /api/v1/auth/register endpoint yet (404 in ~5ms), too fast for Selenium's poll to observe the loading indicator. TimeoutException confirmed live. Blocked on the backend endpoint landing, same as Scenario 5.1's red-selenium; skip marker restored on the test)
- [ ] demo

### 3.2: Login submission shows a loading state
- [x] red-selenium (docker build blocker resolved 2026-07-15; test passed on first run — feature already implemented via green-frontend commit 8cdce1f, no RED state achievable, same class as Scenario 2.3a's confirm sub-case. New test `test_login_submit_loading_indicator_acceptance.py` + `LoginPageStatements.assert_loading_indicator_is_visible`, test-review extracted shared `_assert_visible` helper into `BaseFrontendStatements` to dedupe against RegisterPageStatements. 1 passed)
- [x] red-frontend (LoginForm.test.tsx "shows a visible loading indicator while submitting and removes it once settled"; RED confirmed live — TestingLibraryElementError, no login-loading-indicator element; asserts absence before, className on appearance, and disappearance after settle, closing the coverage gap premortem flagged on Scenario 3.1's register indicator; test-review found nothing to tighten)
- [x] green-frontend (added login-loading-indicator element while isSubmitting, mirroring RegisterForm; also added `role="status"`/`aria-live="polite"` to both Login and Register indicators, addressing the missing-a11y-guard CONCERNS from Scenario 3.1's and this scenario's premortem passes. Refactor extracted shared AuthLoadingIndicator component (commit 8cdce1f). agent-review then flagged the a11y attrs and disappearance-after-settle behavior were unguarded by any test in either LoginForm.test.tsx or RegisterForm.test.tsx despite the commit message claiming coverage — retrofit both test files with role/aria-live/disappearance assertions to close that gap. 11 passed)
- [S] red-frontend-api — no real login API call exists yet, same scoping decision as Scenario 2.3's login test (line 129) and register (line 147): loading state is a pure client-side placeholder via useSubmitPlaceholder, no endpoint to test against
- [S] green-frontend-api — see above
- [x] align-design (no styling changes needed — login mockup has no loading-state styling either, and LoginForm already reuses the shared AuthLoadingIndicator/.auth-loading-indicator aligned in Scenario 3.1. design-review PASS (no hardcoded placeholder data))
- [S] green-selenium (test already passes, see red-selenium note above)
- [S] demo (skipped per convention, see note above)

### 4.1: Password policy hint shown inline
- [x] red-selenium (docker build blocker resolved 2026-07-15, confirmed clean by Scenario 3.2; test passed on first run — pure client-side blur validation already implemented via red-frontend/green-frontend, no RED state achievable, same class as Scenario 2.3a's confirm sub-case and 3.2. New test `test_register_password_policy_hint_acceptance.py` + `RegisterPageStatements.fill_password_field`/`blur_password_field`/`assert_password_policy_error_is_visible`. Fills password field with "weak", blurs via Tab, asserts `register-password-error` testid visible with class `register-hint-error` and exact PASSWORD_POLICY_HINT text. 1 passed. test-review cluster A flagged a loose substring class check (`"register-hint-error" in element.get_attribute("class")`); fixed to split the class attribute into a token list and assert exact membership. Clusters P/S/Se clean (Se's one finding, `navigate_to_register_page`'s direct `driver.get()` nav, is pre-existing shared code, not new — same out-of-scope call as Scenario 3.2's login nav). 1 passed after fix)
- [x] red-frontend (RegisterForm.test.tsx: original 2 tests + strengthened per agent-review/premortem CONCERNS. agent-review flagged the error testid alongside the always-on `.register-hint` risked duplicated on-screen text with no guard — added a test asserting `register-password-hint` is absent when `register-password-error` shows, forcing green-frontend to toggle/replace the hint rather than add a second node. premortem flagged only 2 of 5 policy rules were exercised (weak/'weak' conflates all failures, one compliant string) — added `it.each` covering missing-digit/uppercase/lowercase/special-char/too-short individually, plus a second compliant password with a different special character to catch an overly narrow char-class regex. RED confirmed: 7 failed, 5 passed — matches the new coverage exactly (5 new it.each cases + the hint-duplication test = 6 new failures, plus the original error test = 7; the two compliant-password tests pass trivially since no production code renders an error yet). test-review's exact `toHaveTextContent` (mockup hint copy) on the original test remains the authoritative error text)
- [x] green-frontend (premortem on 151ff19 flagged two more real gaps: no test exercised the invalid→corrected→valid transition on one mount, so an implementation that never clears the error/restores the hint would pass everything; and the "too short" case didn't pin the 8-char boundary. Added a transition test and an exact-8-char compliant case; merged the two compliant-password tests into one `it.each` per the refactor duplication finding. agent-review then caught that the original duplicate-hint guard test queried a `register-password-hint` testid that doesn't exist on the component — vacuous guard, always passing regardless of duplication. Fixed by querying `getAllByText(hintText)` instead (count must stay 1). Final RED: 8 failed, 6 passed. Implementation: extracted `isPasswordCompliant`/`PASSWORD_POLICY_HINT` into a pure `frontend/src/features/auth/utils/passwordPolicy.ts` module (moved from `hooks/` after agent-review flagged it exports no hook; per refactor's design-cluster note, avoids policy logic living inline in JSX and avoids hint/error text duplication — both render the same `PASSWORD_POLICY_HINT` constant). Single `.register-hint` node toggles to `.register-hint-error`/`data-testid="register-password-error"` on blur when non-compliant, rather than rendering a second node. GREEN: 15/15 in RegisterForm, 65/65 full suite. Two post-green review rounds (agent-review + premortem, run concurrently) both independently flagged whitespace being accepted as a "special character" (`/[^A-Za-zА-Яа-я0-9]/` matched spaces) — fixed by excluding `\s` from the special-char class and adding Ёё to the letter classes (also flagged); added a regression test. premortem's second finding — submit is not blocked client-side for a non-compliant, never-blurred password — is out of this scenario's Gherkin scope (02_UI_Tests.md §4.1 only specifies the inline blur message, not submit-gating); noted as a scope decision, not fixed here, deferred to whichever scenario wires the real registration API (3.1/5.x) where server-side rejection already governs correctness)
- [S] red-frontend-api — no API call in this scenario, client-side blur validation only, same scoping decision as prior loading-indicator scenarios (line 147/154)
- [S] green-frontend-api — see above
- [x] align-design (no styling changes needed — error color #ef4444 already matches the mockup's --error CSS variable exactly, error text reuses PASSWORD_POLICY_HINT rather than a separate literal. design-review PASS (no hardcoded placeholder data), test-coverage focus PASS (100% on RegisterForm.tsx and passwordPolicy.ts))
- [S] green-selenium (test already passes, see red-selenium note above)
- [S] demo (skipped per convention, see note above)

### 4.2: Password/confirm mismatch shown inline
- [ ] red-selenium (deferred — docker build blocker, not backend-dependent, same as prior scenarios)
- [x] red-frontend (new file `RegisterForm.confirmPassword.test.tsx`, kept separate from `RegisterForm.test.tsx` to respect the 200-line cap. Learned from 4.1's 4-review-round history and front-loaded coverage in this first commit: (1) basic mismatch shows `data-testid="register-confirm-error"` with text "Пароли не совпадают", (2) no error when matching, (3) duplicate-text guard skipped — RegisterForm's confirm field has no always-visible static hint to duplicate against (checked component structure first, unlike 4.1's vacuous-guard mistake), (4) transition test on one mounted instance: mismatch → blur (error shows) → corrected to match → blur (error clears), (5) edge case: confirm blurred while empty (both empty, or confirm empty/password filled) → no error, mirroring 4.1's empty-password decision, (6) simultaneous-errors case: password invalid AND confirm mismatched → both `register-password-error` and `register-confirm-error` show at once (independent per-field blur handlers, no precedence). RED confirmed: 3 failed / 3 passed — the 3 failures (basic mismatch, transition, simultaneous-errors) all threw `TestingLibraryElementError: Unable to find an element by: [data-testid="register-confirm-error"]` from `getByTestId`, exactly as predicted; the 3 passes (no-error-on-match, empty-confirm, both-empty) pass trivially since no error is rendered today, which already matches the intended behavior. The red-agent had marked the 3 failing tests with `it.skip` — corrected before commit, since this project's convention (established Scenario 1.1 onward) requires RED tests to actually run and fail, never skip-marked. test-review's sub-detectors then flagged real assertion-strictness gaps: two `toHaveTextContent` calls used default substring matching instead of `{ exact: true }`, the transition test's mid-flow assertion only checked presence not the mismatch text, and the simultaneous-errors test never asserted the password-policy error's actual content — all fixed, plus removed stray process-narration comments left in the test file. RED reconfirmed after fixes: 3 failed, 18 passed. refactor extracted a `renderRegisterForm()` helper (6+ verbatim call sites) — real duplication, not premature (commit 80e053e). Concurrent agent-review + premortem both flagged real gaps: agent-review found the password-empty/confirm-filled asymmetry was untested and the empty-suppression rule was asserted without a cited spec basis (spec's Given/When doesn't carve out an empty exception — treating it as UX convention, consistent with 4.1's precedent, now made explicit); premortem found no test covered cross-field staleness — editing the password field after confirm was already validated (matching or mismatched) never re-triggers confirm's check. Added 3 more tests: password-empty/confirm-filled → no error (closes the asymmetry), password changed after confirm validated-matching → error reappears on password blur, password changed to equal an already-mismatched confirm → error clears on password blur. Design decision: confirm mismatch re-validates on ANY blur of either field, not just confirm's own blur. Final RED: 5 failed, 19 passed. Third review round: premortem found "ANY blur re-validates" was underspecified — no test pinned whether confirm must be touched at least once before a password blur can trigger the mismatch check; without that gate, a user who fills both fields and blurs password first (confirm never touched) could see a premature confirm error. Added the "touched" gate test: fill both mismatched, blur password only, confirm never blurred → no error. Final RED: 5 failed, 20 passed. agent-review's follow-up on the same commit surfaced the identical touched-gate finding (already fixed) plus a related but not yet covered sub-case — empty-suppression interacting with cross-field revalidation (password cleared to empty then blurred, while confirm still holds a stale mismatched value) — logged here as a known gap for green-frontend to resolve by design (empty password should suppress the confirm error per the established empty-suppression rule) rather than adding a 4th review round of RED tests; capped strengthening at 3 rounds, consistent with Scenario 4.1's precedent.)
- [x] green-frontend (implemented via two refs (passwordInputRef, confirmInputRef) since inputs are uncontrolled, plus a confirmTouchedRef gate so a password blur only re-triggers confirm validation if confirm has been blurred at least once — closes the premature-validation gap from the 3rd review round. isConfirmMismatched is a pure function (password.length>0 && confirm.length>0 && password!==confirm) mirroring the empty-suppression rule from both fields, which also resolves agent-review's logged sub-case (empty password after cross-field trigger correctly suppresses, since the mismatch check itself requires both non-empty). CONFIRM_MISMATCH_MESSAGE reuses the same single-toggling-node pattern as the password-policy error (no separate always-visible hint to duplicate against, per the original red-agent's check). GREEN: 25/25 in RegisterForm files, 76/76 full suite. Post-green review: refactor moved `isConfirmMismatched`/`CONFIRM_MISMATCH_MESSAGE` into `passwordPolicy.ts` alongside the existing password-policy exports, consistent with the established shared-utils pattern (commit a84af63, 76/76 still green). agent-review PASS — traced all 10 confirm-mismatch tests against the implementation line-by-line, confirmed each passes by genuine logic (ref reads live DOM values at event time, not stale closures); noted the confirm-error div mounts/unmounts (layout shift) vs. the password-error div which only toggles class — not flagged as a defect since `align-design` is the explicit next step for visual reconciliation. premortem CONCERNS: no reset path exists for `passwordError`/`confirmError`/`confirmTouchedRef` when the form succeeds or resets — but `useSubmitPlaceholder` is still a stub with no reset behavior anywhere in the app yet (same latent gap exists for Scenario 4.1's `passwordError` too, not introduced by this commit), so deferred to whichever scenario wires real submit-success handling rather than fixed here.)
- [S] red-frontend-api — no API call in this scenario, client-side blur validation only, same scoping decision as prior scenarios
- [S] green-frontend-api — see above
- [x] align-design (no styling changes needed — error color already matches mockup's --error variable, and the conditionally-mounted error div correctly matches the mockup's lack of reserved space under the confirm field, resolving the layout-shift observation agent-review deferred here. design-review PASS (no hardcoded placeholder data))
- [ ] green-selenium
- [ ] demo

### 5.1: Duplicate-email error displayed on registration
- [ ] red-selenium (deferred — docker build blocker fixed 2026-07-15 (see fix commit removing invalid toHaveTextContent exact option), but this scenario genuinely needs the real backend: `POST /api/v1/auth/register` returns 404, backend layer for Story 7 not started yet, stories.md Backend column is `·`. This is a real cross-layer dependency, not an infra artifact — blocked on the backend session, not deferrable by frontend-only work)
- [x] red-frontend (new file `RegisterForm.duplicateEmail.test.tsx`, first scenario wiring RegisterForm to a real `registerApi.register(email, password)` call, replacing the `useSubmitPlaceholder` scoping decision from 2.3/3.1/4.1/4.2. 5 tests: (1) register called with entered email/password, (2) duplicate-email error (`error_code: "EMAIL_ALREADY_EXISTS"`) renders in `data-testid="register-email-error"` with the server's message, (3) no error while the call is still pending, (4) no error after a successful registration, (5) a previous duplicate-email error clears after a corrected resubmission succeeds. Design note: attempting `vi.mock('../../api/registerApi', () => ({ register: vi.fn() }))` against a not-yet-existing module failed at Vite's import-analysis stage ("Failed to resolve import") before vitest's mocking layer ever engaged — a static `import * as api` must resolve to a real file on disk regardless of the mock factory. This contradicts the task instruction to mock registerApi without creating it; resolved by following this repo's own established red-frontend-api precedent (`documentApi.ts`, commit 1f88266) of creating a minimal stub (`register` throws `Error('Not implemented')`) purely as import scaffolding — no logic, so it does not shortcut the RED state. All 5 tests confirmed RED: assertion failures for (1)/(3)/(4) — `AssertionError: expected "vi.fn()" to be called 1 times, but got 0 times` (RegisterForm never imports/calls registerApi yet); for (2)/(5) — `TestingLibraryElementError: Unable to find an element by: [data-testid="register-email-error"]`. Design tension flagged per task instructions, not silently resolved: wiring a real API call in green-frontend will need to reconcile with the existing `useSubmitPlaceholder`-based disabled-button (2.3) and loading-indicator (3.1) behavior — green-frontend should replace the placeholder's fake delay with the real `registerApi.register` promise while preserving both already-tested behaviors, not add a second competing submit path.)
- [x] green-frontend (`registerApi.ts` now POSTs to `/api/v1/auth/register`, parses `{error_code, message}` on non-ok response, throws `RegisterApiError`. RegisterForm.tsx replaced the shared `useSubmitPlaceholder` hook with a local `handleSubmit`/`isSubmitting` state calling `registerApi.register`; on `EMAIL_ALREADY_EXISTS` sets `emailError` rendered in `data-testid="register-email-error"`, clears on success. Existing disabled-button/loading-indicator wiring preserved (still driven by `isSubmitting`, now set locally). LoginForm/VerifyCodeForm untouched, still use `useSubmitPlaceholder`. 5/5 target tests passed, 81/81 full frontend suite, no regressions.)
- [S] red-frontend (coverage: applyRegisterError ignores non-duplicate-email error codes) — false-branch of errorCode check already correctly no-ops (returns null, emailError stays null, no error rendered); a test would pass immediately, no RED possible, same class as Scenario 1.3's line-73 precedent
- [S] green-frontend (coverage: applyRegisterError ignores non-duplicate-email error codes) — see red step, nothing to implement
- [S] red-frontend-api (coverage: registerApi.register maps a real non-ok HTTP response to RegisterApiError) — verified via a real-fetch test (POST shape, 2xx resolve, 409 duplicate-email reject); all 3 assertions passed on first run with zero implementation changes, no RED achievable, same class as Scenario 1.3 line-73 / this scenario's applyRegisterError precedents
- [S] green-frontend-api (coverage: registerApi.register maps a real non-ok HTTP response to RegisterApiError) — nothing to implement, see red step
- [S] red-frontend-api (coverage: postJson throws HttpError with status+body on non-ok response, falling back to {} when body isn't valid JSON) — postJson's `.catch(() => ({}))` fallback is already correctly implemented; a direct real-fetch test against valid-JSON and invalid-JSON error bodies passed on first run with no code changes, no RED achievable. Third consecutive false-positive coverage gap in this scenario, consistent with the two above
- [S] green-frontend-api (coverage: postJson throws HttpError with status+body on non-ok response, falling back to {} when body isn't valid JSON) — nothing to implement, see red step
- [x] align-design (no styling changes needed — register-email-error reuses the existing `.register-hint.register-hint-error` class already aligned in Scenarios 4.1/4.2, and mounts/unmounts identically to the accepted confirm-error pattern. design-review PASS (no hardcoded placeholder data, message comes from server response at runtime). test-coverage focus found 3 real gaps on the touched files — applyRegisterError's non-duplicate-email branch, registerApi.register's real (non-mocked) error mapping, and postJson's non-ok/invalid-JSON fallback — inserted as 6 new red/green steps above, not fixed inline since each needs its own red-confirmed test)
- [ ] green-selenium
- [ ] demo

### 5.2: Generic invalid-credentials error displayed on login
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.3: Unverified-account error displayed on login
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.4: Account-locked screen displayed after lockout
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.5: Wrong-code error displayed on the verification screen
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.6: Network/timeout error is distinguished from a validation error
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.7: Refreshing the verification-code screen does not trigger an unwanted resend
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.8: Un-submitted registration input is confirmed or restored on navigation away
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.1: "Already have an account? Log in" navigates to the login page
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.2: "Don't have an account? Register" navigates to the registration page
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.3: "Resend code" link, after cooldown, re-issues a code
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.4: Successful verification navigates to the authenticated app shell
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 6.5: "Back to login" from the account-locked screen navigates to the login page
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo
