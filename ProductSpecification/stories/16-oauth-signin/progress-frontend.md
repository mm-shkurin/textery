# Story 16: OAuth sign-in — Frontend Progress

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
- [~] align-design
- [S] green-selenium — deferred
- [S] demo

### 2.1: VK button starts the VK handshake
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — full-page nav, no fetch
- [S] green-frontend-api
- [ ] align-design
- [S] green-selenium
- [S] demo

### 2.2: Yandex button starts the Yandex handshake
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [S] red-frontend-api — full-page nav, no fetch
- [S] green-frontend-api
- [ ] align-design
- [S] green-selenium
- [S] demo

### 3.1: Valid handoff code signs the user in
- [S] red-selenium
- [ ] red-frontend
- [ ] green-frontend
- [ ] red-frontend-api
- [ ] green-frontend-api
- [ ] align-design
- [S] green-selenium
- [S] demo

### 3.2: The exchange is issued exactly once per code
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
