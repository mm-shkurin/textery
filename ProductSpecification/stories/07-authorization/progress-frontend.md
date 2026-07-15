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
- [ ] green-selenium (deferred — requires running backend+frontend containers, out of frontend session's file-ownership scope; resume once backend session/infra available)
- [ ] demo

### 3.2: Login submission shows a loading state
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 4.1: Password policy hint shown inline
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 4.2: Password/confirm mismatch shown inline
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 5.1: Duplicate-email error displayed on registration
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
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
