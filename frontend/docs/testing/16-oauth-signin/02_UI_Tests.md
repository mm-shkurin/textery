<!-- COPIED FILE. Source of truth: ProductSpecification/stories/16-oauth-signin/tests/02_UI_Tests.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# OAuth sign-in — UI Tests

> **Implementation Order**: Tests are numbered for sequential TDD implementation.
> Start with the login-screen button display, then the click→navigation, then the
> `/auth/callback` exchange flow (loading → success), then the error/replay/network
> branches, then redirect safety and the no-regression guard.

Screens: `/login` (`LoginForm` + `OAuthProviderButtons` + `OAuthErrorBanner`) and
`/auth/callback` (`OAuthCallback`). The exchange is `POST /api/v1/auth/oauth/exchange`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Password account | `qa.oauth@textery.test` / `Qa!Oauth2026` (verified) |
| Valid handoff code | `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847` |
| Callback success URL | `/auth/callback?code=hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847&provider=yandex` |
| Callback error URL | `/auth/callback?error=oauth_failed&provider=yandex` |
| Mock exchange session | `{access_token: "eyJhbGciOi…A", refresh_token: "eyJhbGciOi…R", access_token_expires_at: "2026-08-20T12:15:00Z", refresh_token_expires_at: "2026-09-19T12:00:00Z"}` |
| Loading copy | heading `Завершаем вход…`, subtitle `Это займёт пару секунд. Не закрывайте страницу.` (testid `oauth-callback-loading`) |
| Terminal error copy | heading `Не удалось завершить вход`, subtitle `Попробуйте войти ещё раз.` (testid `oauth-callback-error`) |
| Login banner | testid `login-oauth-error`, `role="alert"` |
| Provider failure copy | VK: `Не удалось войти через VK ID. Попробуйте снова.` · Yandex: `Не удалось войти через Yandex ID. Попробуйте снова.` · generic: `Не удалось войти через провайдера. Попробуйте снова.` |
| Network failure copy | `Не удалось связаться с сервером. Проверьте подключение и попробуйте снова.` |
| Code length cap | `512` characters (`OAUTH_CODE_MAX_LENGTH`, inclusive) |

---

## 1. Page Display

### TC-16-UI-1.1 — Login screen shows both OAuth provider buttons

| Field | Value |
|---|---|
| Description | Both providers must be reachable from the login screen and must not read as the primary submit — a user who cannot tell them apart from «Войти» will submit an empty form. |
| Preconditions | A signed-out visitor; `/login` reachable. |
| Test data | Labels `Войти через VK ID` and `Войти через Yandex ID`; testids `oauth-vk-button`, `oauth-yandex-button` |
| Steps | 1. Open `/login`.<br>2. Locate both provider controls below the email/password form.<br>3. Compare their classes with the primary submit button. |
| Expected result | Both controls are visible below the form with exactly those accessible names, under the divider `или`; they carry `btn-oauth btn-oauth-vk` / `btn-oauth btn-oauth-yandex`, which is a different class and appearance from the primary `Войти` submit button; each shows its provider badge as decorative (`aria-hidden`) so the accessible name stays exactly the label. |
| Status | Not run |

---

## 2. Navigation to the provider

### TC-16-UI-2.1 — VK button starts the VK handshake

| Field | Value |
|---|---|
| Description | The handshake is backend-mediated: an XHR here would mean the client holds provider config, and a same-page fetch cannot complete a provider redirect. |
| Preconditions | A signed-out visitor on `/login`; the network log is cleared. |
| Test data | Expected target `/api/v1/auth/oauth/vk/start` |
| Steps | 1. Open `/login` and clear the network log.<br>2. Click `Войти через VK ID`.<br>3. Read the resulting document URL and the network log. |
| Expected result | The browser performs a full-page navigation to `/api/v1/auth/oauth/vk/start` (the control is an `<a href>`, not a button with a fetch); zero XHR/fetch requests are issued by the page; no provider `client_id` or SDK script is loaded in the page. |
| Status | Not run |

### TC-16-UI-2.2 — Yandex button starts the Yandex handshake

| Field | Value |
|---|---|
| Description | The second provider must be wired from the same data list, not a hand-copied branch that can drift to the wrong path. |
| Preconditions | A signed-out visitor on `/login`. |
| Test data | Expected target `/api/v1/auth/oauth/yandex/start` |
| Steps | 1. Open `/login`.<br>2. Click `Войти через Yandex ID`. |
| Expected result | The browser performs a full-page navigation to `/api/v1/auth/oauth/yandex/start`; no XHR is issued from the page. |
| Status | Not run |

---

## 3. Callback success flow

### TC-16-UI-3.1 — Valid handoff code signs the user in

| Field | Value |
|---|---|
| Description | The whole point of the interstitial: spend the code, store the session, and leave no history entry the Back button can walk into (re-spending a dead code). |
| Preconditions | A signed-out visitor; the exchange mock resolves the shared session for the valid code. |
| Test data | Callback success URL; mock exchange session; `sessionStorage` key `authSession` |
| Steps | 1. Open `/auth/callback?code=hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847&provider=yandex`.<br>2. Observe the screen while the exchange is in flight.<br>3. Let the exchange resolve.<br>4. Press the browser Back button. |
| Expected result | Step 2 shows the loading card (`oauth-callback-loading`, `Завершаем вход…`); after step 3 `sessionStorage.authSession` holds both the access and refresh token and the app shell `/` is rendered; the navigation used `replace`, so Back in step 4 does not return to `/auth/callback` and no second exchange is issued. |
| Status | Not run |

### TC-16-UI-3.2 — The exchange is issued exactly once per callback mount

| Field | Value |
|---|---|
| Description | React StrictMode replays the effect; a second POST would spend the one-time code and turn a valid sign-in into a rejection. |
| Preconditions | The app is rendered under StrictMode so the callback effect runs mount → cleanup → remount; the exchange mock counts calls. |
| Test data | Callback success URL; call counter on `oauthExchange` |
| Steps | 1. Mount `/auth/callback` with the valid code under StrictMode.<br>2. Read the exchange mock's call count once the flow settles. |
| Expected result | The call count is exactly `1` for that code; the sign-in still completes (session stored, app shell reached) — the remount does not strand the visitor on the spinner. |
| Status | Not run |

### TC-16-UI-3.3 — A late duplicate rejection after a stored success is ignored

| Field | Value |
|---|---|
| Description | Bouncing an already-signed-in user back to login because a straggler POST was refused would undo a completed sign-in. |
| Preconditions | The callback already exchanged the code and stored a session (the visitor is authenticated). |
| Test data | A second exchange for the same code rejecting with `400` / `error_code = INVALID_OR_EXPIRED_OAUTH_CODE`, arriving after the store |
| Steps | 1. Complete the callback so the session is stored.<br>2. Let the duplicate exchange reject as already-used.<br>3. Read the current route and `sessionStorage.authSession`. |
| Expected result | The user stays on the authenticated app shell; `authSession` is unchanged and still holds the tokens; no `/login` navigation happens and no error banner is shown. |
| Status | Not run |

---

## 4. Callback error handling

### TC-16-UI-4.1 — Provider error / user-cancel returns to login with a distinct message

| Field | Value |
|---|---|
| Description | A cancelled provider sign-in is not a wrong password; showing validation-style copy tells the user to fix a field that is not broken. |
| Preconditions | A signed-out visitor. |
| Test data | `/auth/callback?error=oauth_failed&provider=yandex` |
| Steps | 1. Open the callback error URL.<br>2. Read the route and the rendered banner.<br>3. Inspect the login form's field-error element. |
| Expected result | The visitor is on `/login` (history replaced); the banner `login-oauth-error` with `role="alert"` reads exactly `Не удалось войти через Yandex ID. Попробуйте снова.`; it is a separate element from the field-validation error (`login-form-error`), which is absent; no exchange POST was issued. |
| Status | Not run |

### TC-16-UI-4.2 — Exchange network or server failure is retry-affording

| Field | Value |
|---|---|
| Description | A transport failure is recoverable; leaving the spinner up forever gives the user nothing to do and hides a retriable state. |
| Preconditions | A signed-out visitor; the exchange mock fails with a transport error, a timeout at the shared 25 s httpClient limit, or a `502`. |
| Test data | Callback success URL; failures: network error, 25 s timeout, `502 Bad Gateway` |
| Steps | 1. Open the callback with the valid code and the network error injected.<br>2. Repeat with the timeout, then with the `502`. |
| Expected result | Each run lands on `/login` with the banner `Не удалось связаться с сервером. Проверьте подключение и попробуйте снова.`; the login form is interactive so the visitor can retry; the loading card is gone in every run — no indefinite spinner. |
| Status | Not run |

### TC-16-UI-4.3 — A replayed or expired code shows an error, not a second sign-in

| Field | Value |
|---|---|
| Description | Re-opening the callback URL from history must not silently mint another session; the refusal must be visible. |
| Preconditions | A signed-out visitor (no stored session); the code was already spent. |
| Test data | Callback success URL; exchange mock rejects `400` / `INVALID_OR_EXPIRED_OAUTH_CODE` |
| Steps | 1. Re-open `/auth/callback` with the already-used code.<br>2. Read the screen and `sessionStorage`. |
| Expected result | The terminal error card `oauth-callback-error` is shown (`Не удалось завершить вход` / `Попробуйте войти ещё раз.`); `sessionStorage.authSession` is still absent — no new session was created and the app shell is not reached. |
| Status | Not run |

### TC-16-UI-4.4 — A malformed callback resolves to the error state without an exchange

| Field | Value |
|---|---|
| Description | A crafted or corrupted callback URL must be refused client-side before a POST — an unknown provider or an absurd code is a probe, not a spendable handoff. |
| Preconditions | A signed-out visitor; the exchange mock counts calls. |
| Test data | `?code=abc&provider=twitch`; `?provider=yandex` (no code); `?code=&provider=yandex`; `?code=` + `"a"` × 513 + `&provider=yandex` (the `512` boundary itself is valid) |
| Steps | 1. Open each of the four callback URLs in turn.<br>2. After each, read the screen and the exchange call count. |
| Expected result | Each of the four shows the terminal error card `oauth-callback-error` with `Не удалось завершить вход`; the exchange call count stays `0` across all four; no session is stored and no blank screen or crash appears. |
| Status | Not run |

### TC-16-UI-4.5 — An unrecognized error code falls back to generic copy

| Field | Value |
|---|---|
| Description | The `error`/`provider` values come from the URL and are attacker-influenceable; reflecting them is how markup reaches the screen, and a blank message is no message at all. |
| Preconditions | A signed-out visitor. |
| Test data | `/auth/callback?error=totally_unknown_reason&provider=hackerman` |
| Steps | 1. Open that URL.<br>2. Read the banner text and the page's DOM. |
| Expected result | `/login` shows the generic banner `Не удалось войти через провайдера. Попробуйте снова.`; the strings `totally_unknown_reason` and `hackerman` appear nowhere in the rendered DOM. |
| Status | Not run |

### TC-16-UI-4.6 — A 200 exchange without a usable token fails closed

| Field | Value |
|---|---|
| Description | A `200` is not a sign-in; storing a blank credential lands the user in an app that behaves as signed out and loops them back through login. |
| Preconditions | A signed-out visitor; the exchange resolves `200` with an unusable access token. |
| Test data | Bodies with `access_token` absent, `null`, `""`, and `"   "` (whitespace only) |
| Steps | 1. Open the callback with the valid code, exchange resolving `200` and no `access_token`.<br>2. Repeat for `null`, `""`, and `"   "`.<br>3. After each, read `sessionStorage` and the route. |
| Expected result | In all four runs `sessionStorage.authSession` is absent; the terminal error state is shown and the visitor never reaches the app shell. |
| Status | Not run |

---

## 5. Redirect safety

### TC-16-UI-5.1 — The post-sign-in redirect target is validated

| Field | Value |
|---|---|
| Description | A redirect target taken from anything a caller controls is an open redirect — a phishing hand-off carried out by our own sign-in. |
| Preconditions | A signed-out visitor; the exchange mock resolves a valid session. |
| Test data | Crafted targets `https://evil.test/steal`, `//evil.test`, `/\evil.test`, `/\/evil.test` supplied in the callback router state |
| Steps | 1. Open the callback with the valid code and a crafted target in state.<br>2. Let the exchange succeed.<br>3. Read the resulting URL. |
| Expected result | The visitor lands on the in-app default `/` for every crafted target; the document origin never becomes `evil.test`; no navigation to the external target occurs. |
| Status | Not run |

---

## 6. No regression

### TC-16-UI-6.1 — Email + password login is unchanged

| Field | Value |
|---|---|
| Description | The OAuth buttons and the callback route were added around the existing login; the original path must be untouched. |
| Preconditions | The verified password account exists. |
| Test data | `qa.oauth@textery.test` / `Qa!Oauth2026` |
| Steps | 1. Open `/login`.<br>2. Enter the email and password and submit `Войти`.<br>3. Read the route and `sessionStorage`. |
| Expected result | `POST /api/v1/auth/login` answers `200 OK`; `authSession` holds the access and refresh token; the app shell `/` is rendered; the OAuth banner `login-oauth-error` never appears on this path. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the login screen` | `/login` route rendering `LoginForm` |
| `the OAuth callback screen` | `/auth/callback` route component |
| `a valid handoff code` | `?code=<opaque>` param, exchange mock resolves a session |
| `the VK/Yandex start endpoint` | `GET /api/v1/auth/oauth/{vk\|yandex}/start` (full-page nav) |
| `the exchange` | `POST /api/v1/auth/oauth/exchange` `{ code }` |
| `the session is stored` | `authSession` (sessionStorage) holds access+refresh JWT |
| `an error parameter` | `?error=<code>` on the callback URL |
| `the app shell default` | `safeRedirectTarget` fallback in-app path |
