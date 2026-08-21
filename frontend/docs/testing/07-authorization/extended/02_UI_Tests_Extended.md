<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/extended/02_UI_Tests_Extended.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Authorization — UI Tests (Extended)

Screens: `/register`, `/verify`, and the account-locked screen rendered in place of the
login form. Components live in `frontend/src/features/auth/components/`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account V (verified) | `qa.auth.verified@textery.test` / `Qa!Verified2026` |
| Verification code | `042917` |
| Password policy hint | `Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол` |
| Key test ids | `register-password-input`, `verify-code-input-0`…`-5`, `verify-resend-countdown`, `verify-resend-button`, `account-locked-screen`, `account-locked-countdown`, `login-email-input` |

---

## TC-07-UI-E1 — Password strength indicator updates as the user types

| Field | Value |
|---|---|
| Description | A hint that only appears on blur lets the user finish a non-compliant password before learning anything; live feedback is what makes the policy usable. |
| Preconditions | The user is on `/register` with an empty password field. |
| Test data | Typed in sequence: `q` → `qa` → `qa2026` → `Qa2026` → `Qa!2026` → `Qa!Auth2026` |
| Steps | 1. Type each character of `Qa!Auth2026` into `register-password-input` one at a time.<br>2. Read the strength/hint element after each keystroke. |
| Expected result | The indicator re-renders on every keystroke without a blur; it reports non-compliance while any policy rule is unmet (showing `Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол`) and flips to the compliant state exactly when the value reaches 8+ characters with a digit, an uppercase, a lowercase and a special character. |
| Status | Not run |

## TC-07-UI-E2 — Verification code paste fills all six boxes at once

| Field | Value |
|---|---|
| Description | Users copy the whole code, not one digit at a time; a paste that lands entirely in the first box (or gets truncated to one character) makes the screen feel broken. |
| Preconditions | The user is on `/verify` with all six boxes empty and `verify-code-input-0` focused. |
| Test data | Clipboard contents `042917` |
| Steps | 1. Paste `042917` into `verify-code-input-0`.<br>2. Read the value of each of the six inputs.<br>3. Read `document.activeElement`. |
| Expected result | The boxes hold `0`, `4`, `2`, `9`, `1`, `7` in order — one digit each, none truncated and none left empty; focus rests on `verify-code-input-5`, so the code can be confirmed without further clicks. |
| Status | Not run |

## TC-07-UI-E3 — Countdown timer on verification screen updates every second

| Field | Value |
|---|---|
| Description | A frozen `01:00` is a rate-limit hint that neither counts nor limits — and the resend button never unlocks, stranding a user whose code expired. |
| Preconditions | The user is on `/verify` with the resend cooldown just started; timers are controllable (fake timers or a 3-second real wait). |
| Test data | Countdown starting at `01:00`; readings taken at +1 s, +2 s, +3 s |
| Steps | 1. Read `verify-resend-countdown`.<br>2. Advance one second and read it again.<br>3. Repeat twice more. |
| Expected result | The readings are exactly `01:00`, `00:59`, `00:58`, `00:57` — decrementing by one second per tick in `MM:SS` form, never static and never showing `NaN`. |
| Status | Not run |

## TC-07-UI-E4 — Account-locked countdown updates and auto-enables retry when it reaches zero

| Field | Value |
|---|---|
| Description | If the screen does not react to its own countdown reaching zero, the user must guess that a manual reload is now allowed — the lock looks permanent. |
| Preconditions | The account-locked screen is displayed after `403 ACCOUNT_LOCKED` with `Retry-After: 3`; timers are controllable. |
| Test data | `retryAfterSeconds = 3`; readings at 0 s, 1 s, 2 s, 3 s |
| Steps | 1. Read `account-locked-countdown`.<br>2. Advance the clock one second at a time to zero, reading it each tick.<br>3. Observe the screen at zero, without reloading the page. |
| Expected result | The countdown reads `00:03`, `00:02`, `00:01`, `00:00`; on reaching zero the `account-locked-screen` is dismissed automatically and the login form (`Вход в Textery AI`, `login-email-input`) is shown again with no manual page reload. |
| Status | Not run |
