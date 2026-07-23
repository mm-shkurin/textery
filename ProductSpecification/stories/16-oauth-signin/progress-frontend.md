# Story 16: OAuth sign-in — Frontend Progress

> CARRIED GATE DEBT: `ca78e2d` (3.1 red-frontend-api) landed clean but its post-commit refactor
> batch + the two review passes were cut by a session limit. The test is tiny and born-green, so
> `/refactor` is almost certainly a no-op — re-run over `ca78e2d` only if a gate record is wanted.

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
- [x] align-design — aligned `/auth/callback` to `mockups/desktop/02-callback-loading.html`. The
  structural CSS duplicated the shared shell verbatim (width 420 / surface / subtle border /
  radius 16 / margin 48 auto — identical values in the mockup), so the card now reuses
  `.auth-card` + `.auth-subtitle` (`AuthForm.css` imported, as this is a standalone route —
  AccountLockedScreen renders inside login and doesn't need it) and `OAuthCallback.css` keeps
  only the real deltas: mockup card padding `48px 40px`, `text-align:center`, the conic-gradient
  spinner, `h1` mb 8, subtitle line-height 1.5. **This also fixed a live defect: the error state's
  `<h1>`/`<p>` carried no shared classes, so `oauth-callback-error` rendered browser-default
  32px type and unstyled body copy.** h1 stays the app-standard 28px rather than the mockup's
  22px, for cross-auth-screen consistency (same call as AccountLockedScreen). design-review:
  PASS — the mockup's `Завершаем вход через VK ID` provider name was deliberately NOT hardcoded
  (per-session data; if the heading should name the provider it must come from the query/exchange).
  test-coverage --focus: OAuthCallback 95.45% line / 58.33% branch, `oauthExchangeApi` 100% line /
  66.66% func — every gap is a 4.x error path (rejected exchange `.catch`, missing `code` param,
  unmount-before-resolve), already scheduled as 4.2/4.4; no new steps needed.
- [S] green-selenium
- [S] demo

### 3.2: The exchange is issued exactly once per code
> CARRIED (agent-review + premortem CONCERNS on 3.1 align-design `d2be610`, both non-blocking):
> (a) [CLOSED by 3.2 red-frontend's born-green test 2] the callback's whole shell hung on one `import './AuthForm.css'` line plus the
> `auth-card`/`auth-subtitle` classnames — an import tidy-up drops the shell back to a naked box
> and NO test can go RED (jsdom applies no CSS). Add a class-contract assertion in a callback
> render test: `oauth-callback-loading` has `auth-card`, subtitle has `auth-subtitle`.
> (b) `.oauth-callback-card{padding:48px 40px}` beats `.auth-card{padding:40px}` only by import
> order — equal specificity. Tighten to `.oauth-callback-card.auth-card` (cosmetic, no test possible).
> (c) `.auth-card` has `width:420px` with no `max-width:100%` (the rewrite dropped the callback's
> own one) — overflows under 420px viewports; the same gap already exists for login/register, so
> the fix belongs on `.auth-card`, not here.
> CARRIED (premortem on 3.1 green `2b80323`, REMOTE→own here): OAuthCallback's `hasExchanged` ref
> + per-run `active` flag interact under React StrictMode's mount→cleanup→remount: run 1 sets
> `hasExchanged=true` and `active1=true`, cleanup sets `active1=false`, run 2 returns early on the
> ref and never arms a new `active`; when exchange 1 resolves it sees `active1===false` → stores/
> navigates NOTHING (dev-only permanent spinner). **3.2 must assert AT-LEAST-once (exchange fires
> AND the sign-in completes) under a double-mount, not only at-most-once** — otherwise the once-guard
> can regress into a zero-execution hang. Fix likely: drop the `active` teardown for the success
> path, or key the guard so the surviving run completes.
- [S] red-selenium
- [x] red-frontend — REAL RED. New `OAuthCallback.exactlyOnce.test.tsx` (2 tests). Test 1 (skipped,
  the RED one) mounts the callback under `StrictMode` and asserts BOTH directions in one test:
  at-most-once (`oauthExchange` called exactly once with `{code}` — already true today) AND
  at-least-once (`saveSession` then `navigate` each once — the failing half). Asserting both is the
  point: green cannot satisfy it by tightening the guard, only by making the surviving run complete,
  and any "fix" that cancels the winner leaves saveSession/navigate at 0. **Predicted:** AssertionError,
  `expected "vi.fn()" to be called 1 times, but got 0 times` at line 96 (`saveSession`), 1 failed 1 passed.
  **Actual:** exactly that at 96:37, 1 failed 1 passed. **Match** on type/message/location/status.
  (Prediction revision 1 named the symbol `saveSession`; vitest renders anonymous mocks as `vi.fn()` —
  future predictions against these seams must use the `vi.fn()` label.) Test 2 is born-green (enabled):
  the carried 3.1 (a) shell class-contract guard — `oauth-callback-loading` class is exactly
  `auth-card oauth-callback-card`, subtitle is a `P` with exactly `auth-subtitle oauth-callback-subtitle`
  — so an `AuthForm.css` import tidy-up or a classname rename goes RED where jsdom's no-CSS blindness
  otherwise hides it. test-review: 5 fixes (exact `class` attribute over partial `toHaveClass` on both
  tests, exact heading + subtitle text over regex substring, tag-name pin). Carried (b) padding
  specificity and (c) `.auth-card` `max-width` stay carried — CSS-only, untestable in jsdom, and (c)
  belongs on the shared rule. Suite 319 passed / 1 skipped, tsc clean, file 122L.
- [x] green-frontend — fixed the StrictMode double-mount hang. Replaced OAuthCallback's per-run
  local `active` flag with a shared `mountedRef` (dedicated mount/cleanup effect: mount→true,
  cleanup→false); exchange `.then`/`.catch` gate saveSession/setFailed/navigate on `mountedRef.current`.
  StrictMode remount re-arms the ref→true so the surviving in-flight exchange completes; genuine unmount
  leaves it false (no post-unmount setState). `hasExchanged` ref untouched → POST still fires once. ONE
  uniform gate serves all branches (success/reject/saveSession-false). Un-skipped the RED test (now
  green: at-most-once AND at-least-once). Honored all three carried CONCERNS: (i) folded 2 born-green
  StrictMode guards — exchange-rejects→`oauth-callback-error`, saveSession-false→`oauth-callback-error`
  — proving the fix serves the error branches, not just success; (ii) skipped 1→0, passing +3 (319/1skip →
  **322/0skip**); (iii) tightened scenario 3.2 title in `02_UI_Tests.md` to "…once per callback mount"
  (guard is per-instance; gherkin already same-instance). tsc + oxlint clean; both files ≤200 (87/168).
  > CARRIED (agent-review + premortem CONCERNS on 3.2 red `f3ce139`), green MUST honour all three:
  > (i) **premortem CREDIBLE — the fix proposed in the 3.2 carry-over ("drop the `active` teardown
  > for the success path") repairs only the branch the RED test watches.** The same stale-`active`
  > flag also gates `.catch(() => setFailed(true))` and the fail-closed `if (!stored)` arm, so a
  > success-path-only fix leaves the ERROR screen never rendering under double-mount — green passes,
  > the eternal spinner survives on the rejected-code path. Fold in two more tests: `oauth-callback-error`
  > appears under StrictMode when the exchange REJECTS, and when `saveSession` returns false.
  > (ii) both passes flagged the same thing: the RED case is `it.skip`, so a green that fixes the
  > component but forgets the un-skip leaves the suite green and the regression uncovered. Green's
  > verification must assert the ENABLED count moves (319 passed / 1 skipped → 321 / 0 skipped),
  > not merely "suite green".
  > (iii) agent-review: the scenario title says "exactly once **per code**", but `hasExchanged` is a
  > `useRef` — per component INSTANCE. A genuine remount (route re-entry, Fast Refresh, parent `key`
  > change) makes a fresh ref and fires a second POST with the same single-use code. Either widen the
  > guard to key off the code outside the instance, or narrow the scenario's claim in `02_UI_Tests.md`
  > to same-instance double-effect — do not leave the title broader than the guard.
- [S] red-frontend-api — client-dedup behavior, no new API contract
- [S] green-frontend-api
- [S] align-design — no new UI
- [S] green-selenium
- [S] demo

### 3.3: A late duplicate rejection after a stored success is ignored
- [S] red-selenium
- [x] red-frontend — REAL RED. New `OAuthCallback.lateDuplicateRejection.test.tsx` (91L, it.skip).
  Real scenario behind the 3.2 premortem cross-mount carry: a genuine callback remount (fresh Router
  → fresh `hasExchanged` ref) fires a SECOND POST with the spent one-time code; backend rejects
  already-used; current `.catch` calls `setFailed(true)` unconditionally → the already-signed-in user
  is thrown onto the error screen. Test mocks `isAuthenticated: () => true`, rejects the exchange,
  asserts `navigate('/',{replace:true})` once AND `oauth-callback-error` absent. **Predicted:**
  AssertionError, `expected "vi.fn()" to be called 1 times, but got 0 times` at line 74 (navigate),
  1 skipped-when-off / RED. **Actual:** exactly that at 74:22. **Match** on type/message/location/status.
  test-review: 3 strict seam fixes (non-vacuous `isAuthenticated` called-once, exchange pinned
  `{code}`×1, `saveSession` not-called on the rejection path). Suite 322 passed / 1 skipped.
- [x] green-frontend — added the `isAuthenticated()` branch to OAuthCallback's `.catch`: on a
  rejection, if a session is already stored, `navigate('/',{replace:true})` (benign late/duplicate) —
  else `setFailed(true)` as before. Un-skipped the RED test. Suite 322/1skip → **323/0skip**, tsc +
  oxlint clean, OAuthCallback.tsx 96L. **DECLINED the scoping carry (a) below with rationale:** (1) the
  spec is deliberately broad — 16_OAuthSignin.md:49-50 / Notes:48-50 say ANY "late/duplicate exchange
  rejection after a session was already stored is ignored"; scoping to one error code and re-erroring on
  other authenticated rejections would CONTRADICT the spec. (2) The premortem's stale/expired-token
  mechanism doesn't apply — tokens live in sessionStorage (authSession.ts:5-9), tab-scoped, so
  `isAuthenticated()` true at the callback means signed-in THIS tab session; an expired access token is
  the app session/refresh layer's concern, not the callback's. (3) The RED test rejects with a plain
  `Error` (no `errorCode`), so a code-scoped guard couldn't satisfy it. No companion test added (it would
  encode behavior the spec forbids); no RED assertion touched. The 4.x unauthenticated branches (4.2
  network/5xx, 4.3 replay) own the distinct error copy for the NOT-yet-authenticated flow.
  > CARRIED (premortem CREDIBLE + agent-review CONCERNS on 3.3 red `f8887dd`) — DECLINED, see above:
  > (a) **premortem CREDIBLE — `isAuthenticated()` is a bare presence check (`Boolean(getAccessToken())`,
  > authSession.ts:81), NOT validity.** Redirecting on ANY `.catch` when a token exists is fail-OPEN:
  > a network drop / 500 / genuinely-bad code while a stale or unrelated token sits in sessionStorage
  > silently lands the user in the app shell on dead/wrong credentials — the opposite of the `.then`
  > path's deliberate fail-closed stance, and can even drop them into a DIFFERENT account (wrong
  > identity). Scope the benign redirect to the **already-used / duplicate error code ONLY**, not to
  > session presence — the exchange rejection must carry a discriminable error code (mirror
  > `toAuthApiError`/`errorCode` from oauthExchangeApi). Fold in a companion green test: a
  > NON-duplicate rejection (network/500/invalid) while `isAuthenticated()` is true STILL renders
  > `oauth-callback-error` and does NOT navigate.
  > (b) agent-review (low): the 3.3 red only covers the authenticated=true side; the false-branch
  > guard lives implicitly in `OAuthCallback.exactlyOnce.test.tsx` (real `isAuthenticated` → false →
  > setFailed). The (a) companion test also closes this by pinning the fail path within 3.3's own file.
- [S] red-frontend-api
- [S] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo

### 4.1: Provider error / user-cancel returns to login with a distinct message
- [S] red-selenium
- [x] red-frontend — REAL RED, both halves (the message must actually be shown). New
  `OAuthCallback.providerError.test.tsx` (2 tests): landing `/auth/callback?error=access_denied&provider=vk`
  fires NO exchange (armed spy `not.toHaveBeenCalled`), `navigate('/login',{replace:true,state:{oauthError:
  'Не удалось войти через VK ID. Попробуйте снова.'}})` once, `oauth-callback-loading` absent; 2nd case
  provider-absent → fallback "…через провайдера…". **Predicted:** AssertionError, `expected "vi.fn()" to
  not be called at all, but actually been called 1 times` (current code fires `oauthExchange({code:''})`,
  ignores `error`), 2 failed. **Actual:** exactly that at :61/:76. **Match.** New `LoginForm.oauthError.test.tsx`
  (2 tests): LoginForm with `location.state.oauthError` shows `login-oauth-error` banner (exact text,
  `role="alert"`), distinct from `login-form-error` (validation absent). **Predicted:** TestingLibraryElementError,
  `Unable to find [data-testid="login-oauth-error"]` (LoginForm never reads `oauthError`), 2 failed. **Actual:**
  exactly that at :37/:43. **Match.** test-review: 3 strict fixes (loading-absent ×2, banner exact `.textContent).toBe`).
  Suite 323 passed / 4 skipped.
- [x] green-frontend — implemented both halves. New `utils/oauthMessages.ts` (19L): VK/Yandex/GENERIC
  constants (exact mockup copy) + pure `oauthProviderFailureMessage(provider)` — exact-match 'vk'/'yandex',
  GENERIC for null/''/unknown, NEVER interpolates the raw provider. New `OAuthErrorBanner.tsx` (24L,
  extracted to keep LoginForm ≤cap): reads `location.state.oauthError`, gates on `isUsableMessage`, renders
  distinct `login-oauth-error` `role="alert"` banner. `OAuthCallback.tsx` (119L): error guard runs BEFORE
  the code/exchange path — `error!==null` → no exchange, `navigate('/login',{replace:true,state:{oauthError:
  oauthProviderFailureMessage(provider)}})` once, renders null (no persistent spinner). `LoginForm.tsx` (200L):
  renders `<OAuthErrorBanner/>` at card top. `AuthForm.css`: `.auth-oauth-error` (align-design pins exact
  treatment). Un-skipped both RED files; folded 4 mandated guards (yandex→Yandex msg; zzz→GENERIC not raw;
  error+code→no exchange+VK msg proving error-before-code; no-state→no banner). Suite 323/4skip → **331/0skip**,
  tsc + oxlint clean, all files ≤200. Carry groups (1)(2) fully honored; (3) partially — DECLINED the optional
  `replaceState` clearing, so the no-state negative pins the direct-GET case but the **Back/re-render banner
  resurrection remains a residual** (premortem #2, CREDIBLE) → carried to align-design/4.x follow-up below.
  > CARRIED (agent-review + premortem CONCERNS on 4.1 red `c58a106`) — (1)(2) honored, (3) partial:
  > (1) **provider mapping under-pinned / raw-render risk (both passes, CREDIBLE).** The RED pins only
  > `vk` + provider-absent. Green MUST map ONLY `vk`→VK-copy and `yandex`→Yandex-copy, and EVERYTHING
  > else (unrecognized `provider=zzz`, missing) → the GENERIC "…через провайдера…" fallback — NEVER
  > interpolate the raw `provider`/`error` value into copy (spec 16_OAuthSignin.md:65 — mapped, never
  > raw; enumeration/XSS-adjacent). Fold in tests: `provider=yandex` → exact Yandex message; `provider=zzz`
  > → GENERIC, and the emitted `oauthError` does NOT contain the raw param. Add `AUTH…YANDEX` message
  > constant to authMessages.
  > (2) **error-before-code ordering (premortem #3, CREDIBLE).** Check `searchParams.get('error')` BEFORE
  > the `code` exchange path. Fold in test: `?error=access_denied&provider=vk&code=abc` fires NO exchange
  > and routes to /login with the VK message — proves error wins over a leftover code.
  > (3) **stale banner (premortem #2, CREDIBLE).** Fold in the negative: a plain `/login` with NO
  > navigation state renders NO `login-oauth-error` banner. Prefer clearing `location.state.oauthError`
  > after first render (replaceState) so Back/re-render doesn't resurrect a stale banner; at minimum pin
  > the no-state negative.
  > (4) agent-review (low): "distinct from validation" is weakly pinned (formError is '' with no submit).
  > Optional — pin that a banner + a real validation error can coexist as separate elements if cheap.
  > NOTE file-size: LoginForm.tsx is 195L — adding the banner + oauthError read will breach the 200 cap;
  > extract (e.g. the banner into a small subcomponent, or the state read into a helper) to stay under.
- [S] red-frontend-api — callback param, no API call
- [S] green-frontend-api
- [x] align-design — pinned `.auth-oauth-error` to mockup 03 `.error-banner`: was reusing the amber
  network treatment; now the red boxed alert — `display:flex;align-items:center;gap:10px`, `var(--error)`
  text (#ef4444 = the mockup's literal rgba(239,68,68)), `rgba(239,68,68,0.1)` bg / `0.3` border,
  radius 10, padding 12px 14px, margin-bottom 20px, 14px — plus a leading inline alert-circle SVG (lucide
  glyph, `currentColor`, aria-hidden + text-free so the banner's `textContent` stays exactly the pinned
  message; 8/8 tests still green). No icon dependency (no lucide/svg convention existed in auth).
  design-review: PASS (message is `{oauthError}` from router state — the mockup's hardcoded "…VK ID…"
  placeholder was NOT copied in; `--error` resolves from app-wide index.css:1 `:root`). test-coverage
  --focus: OAuthErrorBanner 100% line/branch (both isUsableMessage arms covered), suite 331/0. Files
  ≤200 (banner 42L, AuthForm.css 179L). **STALE-BANNER RESIDUAL STILL DEFERRED** — the `replaceState`
  clear is a behavior change, not styling; kept out of align-design to preserve TDD discipline. Re-carried
  to a 4.x follow-up below.
  > CARRIED (premortem #2 on 4.1, CREDIBLE, non-blocking) — STILL OPEN, deferred past align-design (it's a
  > behavior change needing its own red/green, not a styling fix): the oauth-error banner reads immutable
  > `location.state.oauthError`, so pressing Back onto the /login history entry (or any re-render) resurrects
  > a stale "sign-in failed" banner with no failure having occurred. Fix: clear `location.state.oauthError`
  > after first render (`navigate(pathname,{replace:true,state:{}})` in an effect) + pin a test that a second
  > render finds no banner. Cheap, real UX guard — schedule as a small 4.x frontend follow-up.
- [S] green-selenium
- [S] demo

### 4.2: Exchange network or server failure is retry-affording
- [S] red-selenium
- [x] red-frontend — REAL RED. New `OAuthCallback.networkFailure.test.tsx` (141L, describe.skip, 3 tests).
  DESIGN: the `.catch` classifies the unauthenticated failure — network/timeout/5xx → back to /login with a
  retry message; business rejection → terminal error screen (4.3). Reuses the EXISTING `isLoginNetworkError`
  (loginErrorHandling) + `NETWORK_LOGIN_FAILURE_MESSAGE` (authMessages), delivered via the 4.1 banner channel:
  `navigate('/login',{replace:true,state:{oauthError: NETWORK_LOGIN_FAILURE_MESSAGE}})`. Cases: (1) transport
  `new Error('Failed to fetch')` (no errorCode) → route to login; (2) gateway `{errorCode:'UNKNOWN_ERROR',
  status:503}` → route to login; (3) BOUND: business `{errorCode:'INVALID_OR_EXPIRED_OAUTH_CODE'}` → navigate
  NOT called, `oauth-callback-error` shown (born-green — stops green over-routing every failure to login).
  **Predicted:** AssertionError, `expected "vi.fn()" to be called 1 times, but got 0 times` (current `.catch`
  setFailed unconditionally), 2 failed 1 passed. **Actual:** exactly that at :82/:102, 2 failed 1 passed. **Match**
  on type/message/location/status. test-review: 1 fix (non-vacuous exchange spy `toHaveBeenCalledWith({code})`
  ×3). Suite 331 passed / 3 skipped.
- [x] green-frontend — added the network branch to OAuthCallback's `.catch`, BETWEEN the isAuthenticated
  (3.3) and setFailed (4.3) arms: `if (isLoginNetworkError(error)) navigate('/login',{replace:true,state:
  {oauthError: NETWORK_LOGIN_FAILURE_MESSAGE}})`. Reuses the existing classifier + constant. Added a
  `routedAway` state flag (set before the mocked navigate) folded into the render early-return so the spinner
  clears when navigate is stubbed (real router unmounts on replace; the flag covers the test seam) — mirrors
  the `error!==null` null-render. Un-skipped the RED file + folded the carried **timeout** case (`new
  RequestTimeoutError()` → routes to /login, pinning the timeout arm independently of bare-Error). OAuthCallback
  137L, network test 163L, all ≤200; tsc + oxlint clean.
  **CROSS-SCENARIO RECONCILIATION (orchestrator, not green — green correctly refused to edit another test):**
  3.2's `exactlyOnce` double-mount error-branch guard rejected with a bare `new Error('exchange failed')` and
  asserted the terminal error card. Under 4.2's classifier a bare Error is now a transport failure → routes to
  /login, so the two tests demanded opposite outcomes for the same shape. Changed the 3.2 fixture to a
  BUSINESS-shaped rejection `{errorCode:'INVALID_OR_EXPIRED_OAUTH_CODE',message:'expired'}` — preserves that
  test's intent (`.catch` survives StrictMode double-mount → terminal error) without colliding with 4.2's
  transport routing. Suite 331/3skip → **335/0skip** (un-skip 3 network + 1 folded timeout).
  > CARRIED (premortem CONCERNS on 4.2 red `6d3d524`, CREDIBLE, non-blocking; agent-review PASS) — HONORED (timeout case folded): the RED
  > pins the network + 5xx arms but NOT the **timeout** arm the scenario names. `RequestTimeoutError`
  > (shared/api/httpClient) routes to /login correctly today only INCIDENTALLY — it's a bodyless `Error`, so
  > `isLoginNetworkError`'s `!hasProp('errorCode')` branch accepts it, same as the bare-Error transport case.
  > That equivalence is unguarded: any future tightening of `isLoginNetworkError` (e.g. `instanceof TypeError`
  > or a transport allowlist) would silently regress the hung-sign-in path to the terminal `setFailed` screen
  > with NO red going red — the exact dead-end 4.2 exists to prevent. Green MUST fold in a 3rd case: reject the
  > exchange with `new RequestTimeoutError()` (unauthenticated) and assert `navigate('/login',{replace:true,
  > state:{oauthError: NETWORK_LOGIN_FAILURE_MESSAGE}})` — pinning the timeout arm independently of the bare-Error shape.
- [x] red-frontend-api — BORN-GREEN (enabled), pins the api→classifier contract 4.2's callback relies on.
  Extended `oauthExchangeApi.test.ts` (156L) with the REAL `isLoginNetworkError`: (1) transport `TypeError`
  → rethrown untouched (`toBe` identity, no `errorCode`), `isLoginNetworkError` true; (2) codeless 503
  (non-JSON body → `{}`) → `toStrictEqual({errorCode:'UNKNOWN_ERROR',message:'',status:503})`, network true;
  (3) BOUND coded 400 → network false. **Predicted:** all 3 born-green (3.1 shipped postJson→toAuthApiError).
  **Actual:** 3 pass. **Match.** test-review: 1 fix (rethrow-identity `toBe` on case 1). Suite 338 passed / 0 skipped.
- [S] green-frontend-api — already-implemented: the exchange's real mapping (postJson → sessionTokensFromWire
  → toAuthApiError, stamping UNKNOWN_ERROR+status on the codeless path) shipped in green-frontend 3.1; the
  born-green api test above pins the network/5xx shape. Same [S]-class as 3.1's already-covered api leg.
  > NOTE (agent-review + premortem CONCERN on 4.2 api `db20e69`, CREDIBLE but PRE-EXISTING + backend-WIP,
  > SHARED with login — NOT a 4.x frontend step): the retry-vs-terminal fork keys off `status`, which
  > `toAuthApiError` attaches ONLY on the codeless path (apiError.ts:71). So a **coded 5xx** (a 500/503 whose
  > body carries an `error_code`) maps to `{errorCode,message}` with no status → `isLoginNetworkError` false →
  > terminal "sign-in failed", NOT the retry-affording network arm — the dead-end 4.2 exists to prevent. Today
  > unreachable: the backend 400s business errors and FastAPI's default 5xx is codeless (`{detail}`), which
  > lands on the covered path. **For whoever wires the real backend / the security scenarios:** either the
  > backend must emit 5xx as codeless, OR `isLoginNetworkError` must widen to treat `status>=500` as network
  > regardless of errorCode. Deliberately NOT pinned here — pinning the current false would cement the bug.
- [S] align-design — reuses login network-error styling
- [S] green-selenium
- [S] demo

### 4.3: A replayed or expired code shows an error, not a second sign-in
- [S] red-selenium
- [x] red-frontend — BORN-GREEN (enabled). New `OAuthCallback.replayedCode.test.tsx` (92L). The UNauthenticated
  replay path (distinct from 3.3's authenticated late-duplicate): mount unauth with a code, reject
  `oauthExchange` with `{errorCode:'INVALID_OR_EXPIRED_OAUTH_CODE',message:'Код входа истёк'}` → current `.catch`
  (unauth + non-network → `setFailed`) shows `oauth-callback-error`. Pins the 4.3 invariant the 4.2 bound did
  NOT: `saveSession` NOT called (no new session) + `navigate` NOT called (no silent re-login), plus exchange
  fired once with `{code}` and no lingering spinner. **Predicted:** born-green (setFailed path leaves
  saveSession/navigate untouched). **Actual:** 1 pass. **Match.** test-review: 0 fixes (already strict). Suite
  339 passed / 0 skipped.
- [S] green-frontend — already-implemented: the unauthenticated non-network rejection already routes to the
  terminal `oauth-callback-error` via `setFailed` (shipped in 3.1 green, bounded by 4.2's classifier); the
  born-green test above pins the no-session/no-redirect invariant. Nothing to implement.
- [S] red-frontend-api — no new API contract; the exchange wire (reject with coded error) is already
  pinned by 3.1 + 4.2 born-green api tests. Same [S]-class as 4.2 green-frontend-api.
- [S] green-frontend-api — no new API contract (see above).
- [S] align-design
- [S] green-selenium
- [S] demo

### 4.4: A malformed callback resolves to the error state without an exchange
- [S] red-selenium
- [x] red-frontend — REAL RED (4 cases). New `OAuthCallback.malformed.test.tsx` (115L, describe.skip).
  DESIGN: client-side pre-exchange validation inserted AFTER the `error=` check, BEFORE the exchange —
  malformed = provider ∉ {vk,yandex} OR code missing/empty OR code length > **512** (client sanity cap;
  server owns single-use/TTL). Cases: unknown provider `?provider=foo`, empty `?code=`, missing code, over-length
  513-char code — each asserts `oauthExchange` NOT called (armed spy), `oauth-callback-error` shown, no lingering
  spinner, `saveSession`/`navigate` not called. **Predicted:** AssertionError, `expected "vi.fn()" to not be
  called at all, but actually been called 1 times` (current effect fires the exchange unconditionally, ignores
  provider, no length check), 4 failed. **Actual:** exactly that, missing-code confirmed firing `{code:''}`, 4
  failed. **Match** on type/message/status. test-review: 0 fixes (already strict, boundary 513=512+1). Suite 339
  passed / 4 skipped.
- [x] green-frontend — added the pre-exchange guard. New `utils/oauthProviders.ts` (32L): moved `OAUTH_PROVIDERS`
  out of the component (now one-place provider edits), `isValidOAuthProvider`, `OAUTH_CODE_MAX_LENGTH = 512`, pure
  `isMalformedCallback(provider, code)` (provider ∉ {vk,yandex} OR `!/\S/.test(code)` blank/whitespace OR length
  > 512 — strict `>`). OAuthCallback effect: `if (isMalformedCallback(provider, code)) { setFailed(true); return }`
  after the `error=` branch, before the exchange. OAuthProviderButtons imports the shared set (buttons tests stay
  green). Un-skipped RED + folded both carried guards: (1) exactly-512 POSITIVE control fires the exchange (guards
  `>` vs `>=`); (2) whitespace-only `%20%20%20` → no exchange, error (guards `trim`/`/\S/` vs `===''`). Suite 339/4skip
  → **345/0skip**, tsc + oxlint clean, all files ≤200 (OAuthCallback 145).
  > GREEN design: share the `{vk,yandex}` valid set (currently local `OAUTH_PROVIDERS` in OAuthProviderButtons.tsx)
  > + a `OAUTH_CODE_MAX_LENGTH = 512` const; add a pure `isMalformedCallback(provider, code)` guard; in the effect,
  > after the `error=` branch and before the exchange, `if (isMalformedCallback(...)) { setFailed(true); return }`.
  > Reuse the shared provider set in BOTH the buttons and the guard so an added provider updates one place.
  > CARRIED (agent-review + premortem CONCERNS on 4.4 red `517012c`, both CREDIBLE), green MUST fold in 2 tests:
  > (1) **512 boundary is one-sided** — the RED pins only 513 as invalid; nothing pins that an EXACTLY-512-char
  > code is VALID. A green written `code.length >= 512` (off-by-one) passes every RED case yet silently rejects
  > legit max-length codes → terminal error, no sign-in, all-green. Fold in a POSITIVE control: `?code=<'x'.repeat
  > (512)>&provider=vk` FIRES the exchange (`toHaveBeenCalledWith({code})`) and shows NO `oauth-callback-error`.
  > Implement the cap as `> OAUTH_CODE_MAX_LENGTH` (512 valid, 513 first invalid).
  > (2) **whitespace-only code** — the RED pins empty-string + missing but not `'   '`. A `code===''`/`!code` green
  > lets a whitespace code POST. Fold in `?code=%20%20%20&provider=vk` → NO exchange, error shown. Implement
  > emptiness as `code.trim() === ''` (reuse the `/\S/` `isUsableMessage` convention if it fits) so blank-but-present
  > is malformed.
- [S] red-frontend-api — no exchange issued
- [S] green-frontend-api
- [S] align-design
- [S] green-selenium
- [S] demo

### 4.5: An unrecognized error code falls back to generic copy
- [S] red-selenium
- [x] red-frontend — BORN-GREEN guard (enabled). New `OAuthCallback.unknownErrorCode.test.tsx` (1 test):
  lands `/auth/callback?error=totally_unknown_xyz` (unknown/absent provider) → exchange never fired
  (`toHaveBeenCalledTimes(0)`, armed spy), `navigate('/login',{replace:true,state:{oauthError: GENERIC}})`
  once with exact GENERIC string, and the raw `totally_unknown_xyz` value absent from BOTH the emitted
  state AND the DOM. **Predicted:** born-green (4.1 maps message on provider only; `error` is a presence
  trigger, never interpolated/rendered). **Actual:** 1 passed. **Match.** test-review: 2 fixes (added a
  positive-control probe so the raw-value-never-rendered assertion is non-vacuous on the null-render path;
  exchange spy `not.toHaveBeenCalled`→`toHaveBeenCalledTimes(0)`). Suite 354 passed / 0 skipped.
- [S] green-frontend — born-green under 4.1's provider-keyed mapper; guard test already enabled + passing.
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
