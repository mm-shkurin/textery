<!-- COPIED FILE. Source of truth: ProductSpecification/stories/07-authorization/tests/02_UI_Tests.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Authorization — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with page display (no API needed), then interaction, then form submission with
> loading state, then validation feedback, then server response handling, then
> navigation.

Screens: `/register`, `/login`, `/verify`, and the account-locked screen rendered in
place of the login form on a `403 ACCOUNT_LOCKED`. Components live in
`frontend/src/features/auth/components/`.

No prerequisite-guard section applies (no parent-resource dependency).

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account P (pending, unverified) | `qa.auth.pending@textery.test` / `Qa!Auth2026` |
| Account V (verified) | `qa.auth.verified@textery.test` / `Qa!Verified2026` |
| Registered email (for the duplicate case) | `qa.auth.taken@textery.test` |
| Verification code | `042917` (6 digits, leading zero) |
| Password policy hint | `Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол` |
| Mismatch message | `Пароли не совпадают` |
| Key test ids | `register-email-input`, `register-password-input`, `register-confirm-password-input`, `register-submit-button`, `login-email-input`, `login-password-input`, `login-password-toggle`, `login-submit-button`, `login-form-error`, `login-network-error`, `verify-code-input-0`…`-5`, `verify-confirm-button`, `verify-resend-button`, `verify-resend-countdown`, `verify-form-error`, `account-locked-screen`, `account-locked-countdown`, `account-locked-back-to-login` |

---

## 1. Page Display

### TC-07-UI-1.1 — Registration form displays email, password, confirm password fields

| Field | Value |
|---|---|
| Description | The registration screen is unusable if any of the three inputs or the submit control fails to render. |
| Preconditions | Frontend running; the user is signed out. |
| Test data | Route `/register` |
| Steps | 1. Open `/register`. |
| Expected result | The heading reads `Регистрация в Textery AI`; `register-email-input`, `register-password-input` and `register-confirm-password-input` are all visible; `register-submit-button` is visible and reads `Зарегистрироваться`. |
| Status | Not run |

### TC-07-UI-1.2 — Login form displays email and password fields

| Field | Value |
|---|---|
| Description | Same rendering guarantee for the sign-in screen. |
| Preconditions | Frontend running; the user is signed out. |
| Test data | Route `/login` |
| Steps | 1. Open `/login`. |
| Expected result | The heading reads `Вход в Textery AI`; `login-email-input` and `login-password-input` are visible; `login-submit-button` is visible and reads `Войти`. |
| Status | Not run |

### TC-07-UI-1.3 — Verification-code screen displays a 6-digit input and resend action

| Field | Value |
|---|---|
| Description | The mocked code has no email channel, so this screen is the only way in — its six boxes and its resend control must both be present. |
| Preconditions | The user has just registered account P and was routed to `/verify`. |
| Test data | Route `/verify`, mocked code `042917` |
| Steps | 1. Complete a registration and land on `/verify`. |
| Expected result | The heading reads `Введите код подтверждения`; six inputs `verify-code-input-0`…`verify-code-input-5` are visible; `verify-resend-countdown` shows `MM:SS` (starting at `01:00`) next to `verify-resend-button` reading `Письмо не пришло? Отправить код повторно`. |
| Status | Not run |

---

## 2. User Interaction

### TC-07-UI-2.1 — Password field visibility toggle

| Field | Value |
|---|---|
| Description | Without a working toggle, a user who mistypes a masked password has no way to check it before being locked out. |
| Preconditions | The user is on `/login` with the password field masked. |
| Test data | Password value `Qa!Verified2026` |
| Steps | 1. Type `Qa!Verified2026` into `login-password-input`.<br>2. Click `login-password-toggle`. |
| Expected result | Before the click the input's `type` is `password`; after the click it is `text` and the literal string `Qa!Verified2026` is visible on screen. |
| Status | Not run |

### TC-07-UI-2.2 — Verification code input advances focus per digit

| Field | Value |
|---|---|
| Description | Without auto-advance the user must click each of six boxes, and most will type all six digits into the first. |
| Preconditions | The user is on `/verify` with `verify-code-input-0` focused. |
| Test data | Digit `0` (first digit of `042917`) |
| Steps | 1. Type `0` into `verify-code-input-0`.<br>2. Read `document.activeElement`. |
| Expected result | `verify-code-input-0` holds `0` and focus has moved to `verify-code-input-1`. |
| Status | Not run |

### TC-07-UI-2.3 — In-flight submit buttons are disabled to prevent duplicate submission

| Field | Value |
|---|---|
| Description | A second click during an in-flight registration sends a second POST — creating a duplicate-email `409` against the user's own first request. |
| Preconditions | The registration form is filled with valid data; the register API is stubbed with a deferred promise. |
| Test data | `qa.auth.new@textery.test` / `Qa!Auth2026`, response held open |
| Steps | 1. Click `register-submit-button`.<br>2. While the request is pending, click it again.<br>3. Count calls to the register API. |
| Expected result | `register-submit-button` carries the `disabled` attribute while pending, `register-loading-indicator` is shown, and step 3 counts exactly one call. |
| Status | Not run |

### TC-07-UI-2.3a — Verify, resend, and login buttons are also disabled while in flight

| Field | Value |
|---|---|
| Description | The same double-submit hole exists on three more controls; guarding only registration leaves a duplicate verify, a wasted resend, and a doubled login attempt live. |
| Preconditions | The verify, resend-code and login APIs are each stubbed with a deferred promise. |
| Test data | Code `042917`; account V credentials; resend clicked after the countdown reads `00:00` |
| Steps | 1. Click `verify-confirm-button`, then click it again while pending.<br>2. Click `verify-resend-button` after the cooldown elapsed, then click it again while pending.<br>3. Click `login-submit-button`, then click it again while pending. |
| Expected result | Each button carries `disabled` while its request is pending and each API is called exactly once — never twice. |
| Status | Not run |

---

## 3. Form Submission

### TC-07-UI-3.1 — Registration submission shows a loading state

| Field | Value |
|---|---|
| Description | Without visible progress the user assumes the click was missed and clicks again. |
| Preconditions | The registration form is filled with valid data; the API response is held open, then released. |
| Test data | `qa.auth.new@textery.test` / `Qa!Auth2026` |
| Steps | 1. Submit the registration form.<br>2. Observe the screen while the request is pending.<br>3. Release the response. |
| Expected result | `register-loading-indicator` (an `aria-live="polite"` `<output>`) is present from submit until the response arrives, then disappears. |
| Status | Not run |

### TC-07-UI-3.2 — Login submission shows a loading state

| Field | Value |
|---|---|
| Description | Same feedback contract on the login form. |
| Preconditions | The login form holds account V's credentials; the API response is held open, then released. |
| Test data | `qa.auth.verified@textery.test` / `Qa!Verified2026` |
| Steps | 1. Submit the login form.<br>2. Observe the screen while pending.<br>3. Release the response. |
| Expected result | `login-loading-indicator` is present for the whole pending window and gone once the response arrives. |
| Status | Not run |

---

## 4. Validation Feedback

### TC-07-UI-4.1 — Password policy hint shown inline

| Field | Value |
|---|---|
| Description | Without an inline rule the user learns the policy only from a server `400`, one round trip and one lost form later. |
| Preconditions | The user is on `/register`. |
| Test data | Password `parol` (no digit, no uppercase, no special, under 8 chars) |
| Steps | 1. Type `parol` into `register-password-input`.<br>2. Blur the field. |
| Expected result | The hint `Минимум 8 символов, включая цифру, заглавную, строчную буквы и спецсимвол` is shown under the field with the error styling (`register-password-error`, `role="alert"`). |
| Status | Not run |

### TC-07-UI-4.2 — Password/confirm mismatch shown inline

| Field | Value |
|---|---|
| Description | A confirmation typo caught client-side saves the user a rejected submission and a retyped form. |
| Preconditions | The user is on `/register`. |
| Test data | Password `Qa!Auth2026`, confirm `Qa!Auth2027` |
| Steps | 1. Enter the two different values.<br>2. Blur `register-confirm-password-input`. |
| Expected result | `register-confirm-error` is visible with the exact text `Пароли не совпадают`. |
| Status | Not run |

---

## 5. Server Response Display

### TC-07-UI-5.1 — Duplicate-email error displayed on registration

| Field | Value |
|---|---|
| Description | A `409` shown as a page-level toast leaves the user hunting for which field is wrong. |
| Preconditions | `qa.auth.taken@textery.test` already has an account; the API returns `409 {"error_code": "EMAIL_ALREADY_REGISTERED", ...}`. |
| Test data | Registration for `qa.auth.taken@textery.test` with a valid password |
| Steps | 1. Submit the registration form with that email.<br>2. Locate the rendered error. |
| Expected result | An error is rendered in `register-email-error`, directly under the email field (not on the password fields), telling the user the address is already registered. |
| Status | Not run |

### TC-07-UI-5.2 — Generic invalid-credentials error displayed on login

| Field | Value |
|---|---|
| Description | Any wording that differs between "unknown email" and "wrong password" reintroduces the enumeration oracle the API deliberately closed. |
| Preconditions | The API returns `401 {"error_code": "INVALID_CREDENTIALS", ...}` for both cases. |
| Test data | Unknown email `qa.auth.ghost@textery.test`; then account V with `WrongPass1!` |
| Steps | 1. Submit login with the unknown email and read `login-form-error`.<br>2. Submit login with account V and the wrong password and read `login-form-error`. |
| Expected result | Both render the same single message in `login-form-error` (fallback `Не удалось войти`); the text is identical between the two runs and never says the email is unknown or does not exist. |
| Status | Not run |

### TC-07-UI-5.3 — Unverified-account error displayed on login

| Field | Value |
|---|---|
| Description | The user's password was right — telling them "sign-in failed" points them at the one thing that is not the problem. |
| Preconditions | The API returns `403 {"error_code": "UNVERIFIED", ...}`. |
| Test data | Account P credentials |
| Steps | 1. Submit login with account P's credentials.<br>2. Read `login-form-error`. |
| Expected result | The message is exactly `Аккаунт не подтверждён. Введите код подтверждения из письма.` — distinct from the generic failure text and pointing at verification. |
| Status | Not run |

### TC-07-UI-5.4 — Account-locked screen displayed after lockout

| Field | Value |
|---|---|
| Description | Lockout is a whole screen state with a countdown, not a one-line message next to a form the user can keep retrying. |
| Preconditions | The API returns `403 {"error_code": "ACCOUNT_LOCKED", ...}` with `Retry-After: 300`. |
| Test data | Account V credentials; `Retry-After: 300` |
| Steps | 1. Submit login and receive the lockout response.<br>2. Inspect the rendered screen. |
| Expected result | The login form is replaced by `account-locked-screen`, heading `Аккаунт временно заблокирован`, subtitle `Слишком много неудачных попыток входа. Попробуйте снова через некоторое время.`, and `account-locked-countdown` showing `05:00` after the prefix `Повторная попытка через `. |
| Status | Not run |

### TC-07-UI-5.5 — Wrong-code error displayed on the verification screen

| Field | Value |
|---|---|
| Description | Six silent boxes after a rejected code give the user nothing to act on. |
| Preconditions | The API returns `400 {"error_code": "INVALID_OR_EXPIRED_CODE", ...}`. |
| Test data | Submitted code `000000` |
| Steps | 1. Type `000000` into the six boxes and click `verify-confirm-button`.<br>2. Inspect the boxes and the message area. |
| Expected result | The six code inputs take the error styling and `verify-form-error` (`role="alert"`) shows a message saying the code is invalid or expired; the screen stays on `/verify`. |
| Status | Not run |

### TC-07-UI-5.6 — Network/timeout error is distinguished from a validation error

| Field | Value |
|---|---|
| Description | A dropped connection shown as a credential error tells the user their password is wrong when it is not — and an indefinite spinner tells them nothing at all. |
| Preconditions | The login API is stubbed to reject with `TypeError('Failed to fetch')`, and separately with a `502` carrying no `error_code`. |
| Test data | Account V credentials; both failure shapes |
| Steps | 1. Submit login with the transport failure armed.<br>2. Repeat with the `502` armed.<br>3. Compare with the rendering of a `401 INVALID_CREDENTIALS`. |
| Expected result | Both failures render `login-network-error` with `Не удалось связаться с сервером. Проверьте подключение и попробуйте снова.`, retry is possible, no spinner remains; the `401` case renders `login-form-error` instead — a visibly different element and different text. |
| Status | Not run |

### TC-07-UI-5.7 — Refreshing the verification-code screen does not trigger an unwanted resend

| Field | Value |
|---|---|
| Description | An auto-resend on mount burns the code the user is holding and immediately trips the server's 60-second cooldown, so the retry is blocked too. |
| Preconditions | The user is on `/verify` with an active code; a spy is attached to the resend API. |
| Test data | Route `/verify`, active code `042917` |
| Steps | 1. Reload `/verify` in the browser.<br>2. Read the resend-API call count. |
| Expected result | The screen re-renders with the six code boxes and the countdown; the resend API call count is `0` — no `POST /api/v1/auth/resend-code` is issued on mount. |
| Status | Not run |

### TC-07-UI-5.8 — Un-submitted registration input is confirmed or restored on navigation away

| Field | Value |
|---|---|
| Description | Silently discarding a half-filled form makes the user retype an email and two passwords with no warning that they were about to lose them. |
| Preconditions | The user is on `/register` with the email and password fields filled and nothing submitted. |
| Test data | Email `qa.auth.new@textery.test`, password `Qa!Auth2026` |
| Steps | 1. Fill the fields without submitting.<br>2. Click the footer `register-login-link` (in-app navigation).<br>3. Separately, reload the page. |
| Expected result | Step 2 raises a confirm dialog reading `Введённые данные не сохранены. Покинуть страницу регистрации?` and navigation happens only on confirm; step 3 fires the browser's `beforeunload` prompt — in neither case are the values dropped without a prompt or a restore. |
| Status | Not run |

---

## 6. Navigation

### TC-07-UI-6.1 — "Already have an account? Log in" navigates to the login page

| Field | Value |
|---|---|
| Description | A dead cross-link strands a returning user on the wrong form. |
| Preconditions | The user is on `/register` with empty fields (no unsaved-guard prompt). |
| Test data | Link `register-login-link`, text `Войти` |
| Steps | 1. Click `Войти` in the footer line `Уже есть аккаунт?`. |
| Expected result | The URL becomes `/login` and the heading `Вход в Textery AI` is displayed. |
| Status | Not run |

### TC-07-UI-6.2 — "Don't have an account? Register" navigates to the registration page

| Field | Value |
|---|---|
| Description | The mirror link on the login screen. |
| Preconditions | The user is on `/login`. |
| Test data | Link `login-register-link`, text `Зарегистрироваться` |
| Steps | 1. Click `Зарегистрироваться` in the footer line `Нет аккаунта?`. |
| Expected result | The URL becomes `/register` and the heading `Регистрация в Textery AI` is displayed. |
| Status | Not run |

### TC-07-UI-6.3 — "Resend code" link, after cooldown, re-issues a code

| Field | Value |
|---|---|
| Description | A resend control that fires before the countdown ends earns a `429`; one that never re-enables leaves the user with a dead code. |
| Preconditions | The user is on `/verify`; the 60-second countdown has reached `00:00`. |
| Test data | `verify-resend-button`, resend API stubbed to return a new code `551308` |
| Steps | 1. Wait for `verify-resend-countdown` to read `00:00`.<br>2. Click `verify-resend-button`.<br>3. Read the countdown. |
| Expected result | Exactly one `POST /api/v1/auth/resend-code` is sent; the countdown restarts at `01:00` and the button returns to `disabled` until it elapses again. |
| Status | Not run |

### TC-07-UI-6.4 — Successful verification navigates to the authenticated app shell

| Field | Value |
|---|---|
| Description | Leaving the user on the verify screen after a `200` gives them no signal that they are in. |
| Preconditions | The verify API returns `200 {"is_verified": true}`. |
| Test data | Code `042917` |
| Steps | 1. Enter the correct code and click `verify-confirm-button`.<br>2. Observe the screen and the URL. |
| Expected result | `verify-success` shows `Аккаунт подтверждён` and the app navigates off `/verify` to the authenticated shell with the access token stored. |
| Status | Not run |

### TC-07-UI-6.5 — "Back to login" from the account-locked screen navigates to the login page

| Field | Value |
|---|---|
| Description | Without a way back, a locked-out user is stuck on a countdown screen with no control. |
| Preconditions | The account-locked screen is displayed after a `403 ACCOUNT_LOCKED`. |
| Test data | Button `account-locked-back-to-login`, label `Вернуться ко входу` |
| Steps | 1. Click `Вернуться ко входу`. |
| Expected result | The lockout screen is dismissed and the login form (`Вход в Textery AI`, `login-email-input`) is displayed again. |
| Status | Not run |
