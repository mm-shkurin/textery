# Story 16: OAuth sign-in — Frontend Progress

> RESUME NOTE (session limit, 2026-07-22): stopped mid work-unit on **3.1 red-frontend-api**.
> Its behavior commit `ca78e2d` landed clean (born-green 3/3, test-review 0 fixes), but the
> post-commit refactor batch + the two review passes were CUT by the session limit before
> completing — re-run `/refactor` + agent-review + premortem over `ca78e2d` on resume if a gate
> record is wanted (the test is tiny + born-green, so refactor is almost certainly a no-op).
> Next actionable step: **3.1 align-design** (`[~]`) — pixel-match the `/auth/callback` screen
> (`OAuthCallback.tsx` + `OAuthCallback.css`) to mockup `mockups/desktop/02-callback-loading.html`.

Scenarios from `tests/02_UI_Tests.md`. Selenium legs (`red-selenium`/`green-selenium`) are
backend-gated → `[S]` deferred, batched for a full-stack selenium pass once the backend
`/oauth/*` endpoints land (same convention as Story 7). `demo` skipped (visual-only,
non-gating). Frontend builds against a mock of `POST /oauth/exchange`.

## Frontend Scenarios (02_UI_Tests.md)

### 1.1: Login screen shows both OAuth provider buttons
- [S] red-selenium — backend-gated, deferred to full-stack pass
- [x] red-frontend — REAL RED. New `LoginForm.oauthButtons.test.tsx` (3 tests): asserts VK (`oauth-vk-button`) + Yandex (`oauth-yandex-button`) links render via `getByRole('link',{name})` with exact accessible names, each distinct from `login-submit-button` and each other, both below the submit in DOM order. **Predicted:** TestingLibraryElementError, unable to find `[data-testid="oauth-vk-button"]`, 3 failed. **Actual:** exactly that, 3 failed. **Match** on type/message/status. test-review: 3 fixes (substring→exact; DOM-order truthy→exact flag; explicit VK≠Yandex). agent-review + premortem CONCERNS (both): exact `textContent` label conflicted with the mockup's in-button decorative badge → retargeted to accessible name via `getByRole` (badge must be aria-hidden), fixed before green so it wasn't self-contradicting.
- [x] green-frontend — added VK/Yandex links below the submit. New `OAuthProviderButtons.tsx` (33L, provider-as-data array `{provider,label,badge,startPath}` → no per-provider JSX branch); `<a href="/api/v1/auth/oauth/{provider}/start">` full-page nav, `aria-hidden` badge span so accessible name = label; `LoginForm.tsx` 195L (imports the component to stay under the 200 cap); `LoginForm.css` +`.auth-divider`/`.oauth-list`/`.btn-oauth`/`.provider-badge` (vk #0077ff / yandex #fc3f1d). Un-skipped the test. Full suite **273/273**, tsc clean, oxlint clean, all files <200.
- [S] red-frontend-api — pure display, no API call
- [S] green-frontend-api
- [x] align-design — VERIFY-ONLY, no changes. green-frontend already built from the mockup's
  exact values; compared every token against `mockups/desktop/01-login-oauth.html`: divider
  (margin 24px 0, gap 12px, muted, 13px, 1px border-subtle rules), `.btn-oauth` (transparent,
  border-subtle→strong hover, radius 10px, padding 12px 16px, 15px/500, gap 12px), `.provider-badge`
  (28×28, radius 8px, 13px/700, #fff on vk #0077ff / yandex #fc3f1d) — all match; divider+list sit
  OUTSIDE `<form>` per mockup. design-review: PASS (no hardcoded placeholder data — labels/badges/
  routes are static config). test-coverage --focus: OAuthProviderButtons 100% line/branch (data-driven,
  no conditionals). href-value assertion deferred to 2.1/2.2 (carried follow-up).
- [S] green-selenium — deferred
- [S] demo

### 2.1: VK button starts the VK handshake
> CARRIED (agent-review + premortem CONCERNS on 1.1 green `25b7020`): the `href` /
> `startPath` on each OAuth link is currently UNGUARDED — a typo or a VK↔Yandex path swap
> ships green (1.1 asserts only testid/name/order). This scenario (VK) and 2.2 (Yandex) MUST
> assert the exact `href` per provider (`toHaveAttribute('href', '/api/v1/auth/oauth/vk/start')`)
> AND that the control is a PLAIN anchor (full-page nav), not a react-router `<Link>` — a
> `<Link>` would client-route and never reach the backend. Both close this gap.
- [S] red-selenium
- [x] red-frontend — BORN-GREEN guard (enabled, not skipped), closes the carried 1.1 href/anchor gap. New `OAuthProviderButtons.vkHandshake.test.tsx` (56L, 2 tests): pins VK exact href `/api/v1/auth/oauth/vk/start`, `not` the Yandex endpoint (swap guard), plain-anchor via `tagName==='A'` AND a cancelable click asserting `defaultPrevented===false` (a react-router `<Link>` would preventDefault — regression turns it RED), and no background fetch on render/click (spy armed to throw + non-vacuity probe). **Predicted:** born-green, 2 pass (1.1 green already ships the plain `<a>` with correct href). **Actual:** 2 passed. **Match.** test-review: 1 fix (click discriminator from opaque `fireEvent` return → explicit `defaultPrevented` on a named cancelable event).
- [S] green-frontend — born-green, nothing to implement (1.1 already ships the correct plain `<a href>`); guard above pins it.
- [S] red-frontend-api — full-page nav, no fetch
- [S] green-frontend-api
- [S] align-design — no new UI; VK button styled + aligned in 1.1.
- [S] green-selenium
- [S] demo

### 2.2: Yandex button starts the Yandex handshake
- [S] red-selenium
- [x] red-frontend — BORN-GREEN guard (enabled), mirror of 2.1 for Yandex. New `OAuthProviderButtons.yandexHandshake.test.tsx` (57L, 2 tests): pins Yandex exact href `/api/v1/auth/oauth/yandex/start`, swap guard (≠ VK endpoint), plain-anchor via `tagName==='A'` + cancelable click `defaultPrevented===false`, no background fetch (armed spy + non-vacuity probe). **Predicted:** born-green, 2 pass. **Actual:** 2 passed. **Match.** test-review: 0 fixes (already strict). **Together with 2.1 this fully closes the carried 1.1 review CONCERNS — both provider controls now have pinned-href + plain-anchor + no-fetch regression guards.**
- [S] green-frontend — born-green, 1.1 already ships the correct plain `<a href>` for Yandex.
- [S] red-frontend-api — full-page nav, no fetch
- [S] green-frontend-api
- [S] align-design — no new UI; Yandex button styled + aligned in 1.1.
- [S] green-selenium
- [S] demo

### 3.1: Valid handoff code signs the user in
- [S] red-selenium
- [x] red-frontend — REAL RED (first callback-flow scenario). New `OAuthCallback.success.test.tsx` (109L, describe.skip): landing `/auth/callback?code=handoff-abc123&provider=vk` → asserts `oauth-callback-loading` state, `oauthExchange` called once with `{code}`, then `saveSession({accessToken,refreshToken})` (mapped shape) once, then `navigate('/', {replace:true})` once (target from the REAL `safeRedirectTarget`). Created behaviorally-empty stubs `OAuthCallback.tsx` (renders null) + `api/oauthExchangeApi.ts` (throwing stub + `OAuthExchangeRequest`/`OAuthSession` shapes) — REQUIRED because vite `import-analysis` resolves `vi.mock`/import path strings at transform time even under `describe.skip`, so referencing a nonexistent module crashes collection. **Predicted:** TestingLibraryElementError, unable to find `[data-testid="oauth-callback-loading"]` (empty stub renders `<div/>`), exchange/saveSession/navigate never called, 1 failed. **Actual:** exactly that, 1 failed. **Match.** test-review: 2 fixes (added `toHaveBeenCalledTimes(1)` on saveSession + navigate). Full suite 277P/1S, tsc + oxlint clean. **In the refactor batch:** refactor removed a stale duplicate comment; agent-review CONCERNS (misleading "dynamic imports" comment — imports are static; fixed); premortem CONCERNS CREDIBLE — RED didn't force green to check `saveSession`'s return, so a refused store (Safari private mode / webview) would navigate with no token → sign-in loop; **folded a 2nd fail-closed guard test** (`saveSession→false ⇒ NOT navigate('/',{replace:true})`, mirrors LoginForm's guard) so green must honor it. File 135L, 2 skipped.
- [x] green-frontend — implemented the callback flow. New `OAuthCallback.tsx` (69L): reads `code` from `useSearchParams`, renders `oauth-callback-loading`, calls `oauthExchange({code})` exactly once (ref-guarded), maps to session, `saveSession`, and navigates `safeRedirectTarget(undefined)` (`/`) with `{replace:true}` ONLY if the store succeeded — FAIL-CLOSED otherwise (mirrors LoginForm `if(!saveSession)`); a rejected exchange stops the loading state without crashing (rich 4.x handling later). New `oauthExchangeApi.ts` (44L): real `oauthExchange({code})` POSTs `/api/v1/auth/oauth/exchange` via shared `postJson`, snake_case→camelCase map + `toAuthApiError` seam mirroring `loginApi.ts`. New `OAuthCallback.css` (52L, structural; pixel align next). `App.tsx` (37L): `<Route path="/auth/callback">`. **Test-isolation fix (mine, not green — green is tests-read-only): the fail-closed guard I folded in the 3.1 refactor batch lacked mock reset between tests, so test 2 saw saveSession called 2×; added `afterEach` resetting all three seams (mirrors VerifyCodeForm.success), then un-skipped.** Both tests green. Full suite **279/279**, tsc 0, oxlint clean, all files <200.

- [x] red-frontend-api — BORN-GREEN (enabled), api-layer wire contract. New `oauthExchangeApi.test.ts` (94L, real-fetch stub like loginApi.test.ts): pins POST `/api/v1/auth/oauth/exchange` exact URL/method/body `{code}`, snake→camel success map via `toStrictEqual` (4-field OAuthSession, pins `sessionTokensFromWire`), coded-error via shared `toAuthApiError` (`{errorCode,message}`, `toStrictEqual` also proves no stray retryAfter/status on the coded path). **Predicted:** born-green 3 pass (green-frontend already shipped the real mapping). **Actual:** 3 passed. **Match.** test-review: 0 fixes (already strict).
- [S] green-frontend-api — already-implemented: `oauthExchangeApi.ts` (real `postJson` → `sessionTokensFromWire` → `toAuthApiError`) shipped in green-frontend 3.1; the born-green api test above pins it. Same [S]-class as Story 7's already-covered api legs.
- [~] align-design
- [S] green-selenium
- [S] demo

### 3.2: The exchange is issued exactly once per code
> CARRIED (premortem on 3.1 green `2b80323`, REMOTE→own here): OAuthCallback's `hasExchanged` ref
> + per-run `active` flag interact under React StrictMode's mount→cleanup→remount: run 1 sets
> `hasExchanged=true` and `active1=true`, cleanup sets `active1=false`, run 2 returns early on the
> ref and never arms a new `active`; when exchange 1 resolves it sees `active1===false` → stores/
> navigates NOTHING (dev-only permanent spinner). **3.2 must assert AT-LEAST-once (exchange fires
> AND the sign-in completes) under a double-mount, not only at-most-once** — otherwise the once-guard
> can regress into a zero-execution hang. Fix likely: drop the `active` teardown for the success
> path, or key the guard so the surviving run completes.
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — client-dedup behavior, no new API contract
- [S] green-frontend-api
- [S] align-design — no new UI
- [S] green-selenium
- [S] demo

### 3.3: A late duplicate rejection after a stored success is ignored
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo

### 4.1: Provider error / user-cancel returns to login with a distinct message
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — callback param, no API call
- [S] green-frontend-api
- [ ] align-design
- [S] green-selenium
- [S] demo

### 4.2: Exchange network or server failure is retry-affording
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design — reuses login network-error styling
- [S] green-selenium
- [S] demo

### 4.3: A replayed or expired code shows an error, not a second sign-in
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo

### 4.4: A malformed callback resolves to the error state without an exchange
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — no exchange issued
- [S] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo

### 4.5: An unrecognized error code falls back to generic copy
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo

### 4.6: A 200 exchange without a usable token fails closed
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo

### 5.1: The post-sign-in redirect target is validated
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — client-side redirect guard
- [S] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo

### 6.1: Email + password login is unchanged (regression guard)
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo
