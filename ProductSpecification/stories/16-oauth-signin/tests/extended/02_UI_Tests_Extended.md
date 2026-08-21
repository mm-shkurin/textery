# OAuth sign-in — UI Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

Screens: `/auth/callback` (`OAuthCallback`) and `/login` (`LoginForm` + `OAuthProviderButtons`).

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Valid handoff code | `hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847` |
| Loading card | testid `oauth-callback-loading`, heading `Завершаем вход…`, subtitle `Это займёт пару секунд. Не закрывайте страницу.` |
| Terminal error card | testid `oauth-callback-error`, heading `Не удалось завершить вход`, subtitle `Попробуйте войти ещё раз.` |
| Login banner | testid `login-oauth-error`, `role="alert"` |
| Generic provider copy | `Не удалось войти через провайдера. Попробуйте снова.` |
| Start endpoints | `/api/v1/auth/oauth/vk/start`, `/api/v1/auth/oauth/yandex/start` |

---

## 1. Callback edge states

### TC-16-UI-1.1 — Both code and error present on the callback

| Field | Value |
|---|---|
| Description | A URL carrying both is contradictory and attacker-shaped; spending the code anyway would let an error leg be smuggled past into a sign-in. |
| Preconditions | A signed-out visitor; the exchange mock counts calls. |
| Test data | `/auth/callback?code=hc_9f3b7c2a1d4e4f8b9c0a6d5e2f31b847&error=oauth_failed&provider=yandex` |
| Steps | 1. Open that URL.<br>2. Read the screen, the route and the exchange call count. |
| Expected result | The error branch wins: the visitor is returned to `/login` with the provider banner `Не удалось войти через Yandex ID. Попробуйте снова.`; the exchange call count is `0`; no session is stored. |
| Status | Not run |

### TC-16-UI-1.2 — Direct visit to the callback with no parameters

| Field | Value |
|---|---|
| Description | The interstitial is transient; a bookmark or a stray direct visit must resolve, not hang on a spinner waiting for a code that will never come. |
| Preconditions | A signed-out visitor. |
| Test data | `/auth/callback` with no query string at all |
| Steps | 1. Open `/auth/callback`.<br>2. Read the screen and the exchange call count. |
| Expected result | The terminal error card `oauth-callback-error` is shown (`Не удалось завершить вход` / `Попробуйте войти ещё раз.`) with a way back to `/login`; no exchange request is issued; no blank screen and no persistent spinner. |
| Status | Not run |

### TC-16-UI-1.3 — Loading state announces progress accessibly

| Field | Value |
|---|---|
| Description | A screen-reader user gets silence during the exchange unless the transient status is a live region — the page appears frozen. |
| Preconditions | A signed-out visitor; the exchange is held in flight. |
| Test data | Callback URL with the valid code; the `<output aria-live="polite">` status region |
| Steps | 1. Open the callback with the valid code, holding the exchange unresolved.<br>2. Inspect the loading card's accessibility tree. |
| Expected result | The status region is exposed as a polite live region announcing `Завершаем вход…`; the spinner element itself is `aria-hidden="true"` so it adds no noise; the announced text is the Russian copy, not a raw class or testid. |
| Status | Not run |

---

## 2. Button behaviour

### TC-16-UI-2.1 — Provider buttons keep the entered email untouched

| Field | Value |
|---|---|
| Description | The provider controls are not form submits; running the email validator on them would block the navigation with an irrelevant field error. |
| Preconditions | A signed-out visitor on `/login` with a partially filled form. |
| Test data | Email field contains `qa.oau` (an incomplete address); click `Войти через Yandex ID` |
| Steps | 1. Open `/login` and type `qa.oau` into the email field.<br>2. Click `Войти через Yandex ID`.<br>3. Read the field error element and the navigation target. |
| Expected result | The browser navigates full-page to `/api/v1/auth/oauth/yandex/start`; no `login-form-error` validation message is rendered and the email field is not cleared or rewritten before the navigation. |
| Status | Not run |
