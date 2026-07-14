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
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.3: In-flight submit buttons are disabled to prevent duplicate submission
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 2.3a: Verify, resend, and login buttons are also disabled while in flight
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
- [ ] demo

### 3.1: Registration submission shows a loading state
- [ ] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [ ] green-selenium
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
