# Interview: Story 16 — OAuth sign-in (VK ID + Yandex ID)

Follow-up to Story 7 (Authorization), where VK ID / Yandex ID OAuth were explicitly
deferred (`stories/07-authorization/interview.md` Scope). This story picks them up.
Frontend-first: the backend OAuth slice is WIP, so this spec **defines the contract**
the backend will implement, and the frontend is built against a mock of it.

## Scope

In scope this iteration:
- "Войти через VK ID" and "Войти через Yandex ID" buttons on the **Login screen only**.
- Backend-mediated OAuth: the button is a full-page navigation to a backend start
  endpoint; the backend does the whole provider handshake (client secrets never touch the
  client). See Key Decisions.
- A frontend **callback route** (`/auth/callback`) that receives a one-time opaque handoff
  code from the backend, exchanges it for a JWT session, stores it (reusing Story 7's
  `authSession`), and lands the user in the app shell.
- First OAuth sign-in **auto-creates** the account; the provider has already verified the
  email, so the email-verification screen is **skipped** — straight to app shell.
- Error / cancel handling on the callback (provider denied, user cancelled, expired
  handoff code) distinct from a successful sign-in.

Out of scope (explicitly deferred):
- **Account linking / merge** — attaching an OAuth identity to an existing email+password
  account with the same email. First cut: an OAuth identity is its own account. NOT YET
  IMPLEMENTED.
- **Unlink / linked-account management** in the profile. Belongs with Story 13 (Profile).
- OAuth buttons on the **Register screen** — Login-only per this iteration; the login
  screen is the single door.
- **Logout** — there is no logout anywhere yet (same as Story 7); a cross-cutting concern,
  not OAuth-specific. Not added here.
- Refresh-token rotation, and any provider beyond VK ID / Yandex ID.

## External API/Service Documentation (links)

To be filled at `/api-spec` — the provider handshake lives entirely backend-side, so the
frontend does not call these directly, but the contract must reference them:

1. VK ID (VK ID SDK / OAuth 2.1 + PKCE) — `https://id.vk.com/about/business/go/docs`
2. Yandex ID (Yandex OAuth) — `https://yandex.ru/dev/id/doc/`

ACTION (`/api-spec`): pin the exact provider auth URLs, scopes (email + basic profile),
and redirect-URI registration the backend needs. Frontend needs none of these secrets.

## API Endpoints Used (contract DEFINED here, backend to implement)

Provider ∈ `vk | yandex`. All under `/api/v1/auth/oauth`.

1. `GET /oauth/{provider}/start` — **NOT YET IMPLEMENTED (backend WIP).** Full-page
   browser navigation target of the button. Backend 302-redirects to the provider's auth
   page with `client_id`, registered `redirect_uri`, requested scope, and a CSRF `state`.
   Frontend just sets `window.location` to it — no fetch, no JSON.
2. `GET /oauth/{provider}/callback?code=…&state=…` — **backend-only** (the provider's
   redirect target). Backend validates `state`, exchanges the provider `code`, resolves or
   creates the account, mints a **one-time opaque handoff code**, and 302-redirects the
   browser to the frontend: `{FRONTEND}/auth/callback?code=OPAQUE&provider={provider}` on
   success, or `{FRONTEND}/auth/callback?error=CODE` on failure. The frontend never sees
   the provider code or any token in this URL — only the opaque handoff code.
3. `POST /oauth/exchange` — **NOT YET IMPLEMENTED.** Body `{ code }` (the opaque handoff
   code). 200 → the **same session body Story 7 login returns**:
   `{ access_token, refresh_token, access_token_expires_at, refresh_token_expires_at }`
   (snake_case). The handoff code is **single-use** and short-TTL. Errors:
   `400 INVALID_OR_EXPIRED_OAUTH_CODE` (bad / replayed / expired), `5xx` server error —
   both `{ error_code, message }`, the auth error envelope.

## Token/Auth Requirements

- Session shape is byte-identical to Story 7 login, so it flows through the SAME boundary
  mapping (`loginApi` → camelCase) and the SAME `authSession` (sessionStorage) storage.
  No new token model.
- **The token never rides in a URL.** Only the opaque, single-use handoff code appears in
  `/auth/callback?code=…`; it is immediately POSTed to `/oauth/exchange` and the real JWTs
  come back in the response body. This is the whole reason for the one-time-code hop
  instead of tokens-in-fragment — it honours Story 7's "code/token never in URL" stance
  (`07_Authorization_Notes.md`).

## Key Architectural Decisions

DECISION: **Backend-mediated redirect**, not client PKCE and not provider JS SDK widgets.
The client holds no provider `client_id`/secret and loads no third-party script — keeps
the frontend self-contained and the secrets server-side (`infra/.env`).

DECISION: **One-time opaque handoff code** for the session hop (chosen over
tokens-in-URL-fragment and over httpOnly cookies). Fragment leaks the token into history/
logs; httpOnly cookies would need cookie infra the app doesn't have yet. The opaque code
is single-use and short-TTL, so a leaked callback URL is inert after first exchange.

DECISION: **Login-only** entry. One door. Register-screen buttons and a dedicated
method-chooser screen are deferred.

DECISION: **Auto-create on first sign-in, skip verify.** The provider asserts the email,
so re-verifying via a mocked code would be pointless friction. New OAuth users land in the
app shell directly.

DECISION: reuse the existing `/auth/callback`-style routing in the plain `<BrowserRouter>`
(App.tsx) — a new `<Route path="/auth/callback">` component. No data-router migration
(same constraint Story 7 recorded: `useBlocker` unavailable).

## Business Rules & Constraints

- Two providers only: `vk`, `yandex`. An unknown `provider` value on the callback route is
  an error state, not a crash.
- The handoff code is single-use: a second exchange of the same code MUST fail
  (`INVALID_OR_EXPIRED_OAUTH_CODE`) — so a browser back/refresh onto `/auth/callback` after
  a successful sign-in shows an error, not a second silent login.
- Provider error / user-cancel (`/auth/callback?error=…`) returns the user to the login
  screen with a clear, non-technical message — distinct from a validation error, mirroring
  Story 7's network-vs-validation error treatment.
- Exchange in flight: show a loading state on the callback screen; a failed exchange
  (network/timeout/5xx) is retry-affording (back to login), never an indefinite spinner —
  reuse the shared `httpClient` 25s timeout and login's network-error class.
- Redirect target after success is validated with the existing `safeRedirectTarget`
  (in-app absolute path only) — an `error`/`code` callback param must never become an
  open-redirect vector.

## Already Implemented (REUSE)

- `frontend/src/features/auth/utils/authSession.ts` — sessionStorage JWT storage; the
  OAuth session stores through it unchanged.
- `frontend/src/features/auth/api/apiError.ts` + `loginApi` mapping — same session body
  and same `{ error_code, message }` envelope, so the exchange response maps through the
  existing boundary.
- `frontend/src/shared/api/httpClient.ts` — shared 25s reject-only timeout applies to the
  exchange POST for free.
- `frontend/src/features/auth/utils/safeRedirectTarget.ts` — reuse for the post-sign-in
  target.
- `LoginForm.tsx` + `AuthForm.css` — the buttons mount here; network/error-state patterns
  (`login-network-error`, form-owned copy in `authMessages`) are the template for the
  callback screen's error handling.
- Login mockup `stories/07-authorization/mockups/**/03-login.html` — the base the OAuth
  buttons are added onto at `/mockups`.

## NOT Yet Implemented (Gaps)

- **Frontend:** VK/Yandex buttons on `LoginForm` (full-page nav to `/oauth/{provider}/
  start`); a new `/auth/callback` route component (read `code`/`error`/`provider`, POST
  exchange, store session, navigate — with loading + error + single-use-replay states);
  a new `oauthExchangeApi` in the auth api layer; provider→label/icon config.
- **Backend (WIP, this spec is its contract):** all three endpoints above, provider client
  registration + secrets in `infra/.env`, the OAuth-identity → account resolution
  (auto-create, no verify), and the one-time handoff-code store (single-use, TTL).
- **Mock for frontend-first build:** a mocked `/oauth/exchange` (and a way to simulate the
  callback redirect) so the frontend flow is testable before the backend lands — same
  spirit as Story 7's mocked verification code.

## Cross-Story Dependencies

- **Story 7 (Authorization)** — this reuses its session model, storage, api-error mapper,
  and login screen; must not regress the email+password flow.
- **Story 13 (Profile)** — will own linked-account management / unlink (deferred here).
- **Story 8 (Billing)** — an OAuth-created account is still a `User`; tariff assignment
  applies the same as an email+password account (no OAuth-specific billing work here).

## Security Considerations

- CSRF `state` on the provider handshake is a **backend** responsibility; the frontend's
  job is to never trust the callback params beyond the opaque code and to validate the
  redirect target (`safeRedirectTarget`).
- The opaque handoff code is a credential for its single-use lifetime — never log it,
  never leave it in a persisted URL after exchange (replace history on success).
- Account-linking is deferred, which means: if an email+password account and an OAuth
  sign-in share an email, first cut creates a **separate** account. Flag explicitly before
  any production rollout (a real user would expect one identity) — the linking story
  closes this.

## Testing Considerations

- The frontend flow is testable end-to-end against a **mocked** exchange endpoint (Story
  7's pattern). Drive: click VK button → assert full-page nav to the start URL; land on
  `/auth/callback?code=…` → assert exchange POST → session stored → app-shell nav; and the
  three failure branches (`error=` param, exchange 400 replay, exchange network/5xx).
- Selenium legs that need the real provider handshake are backend-gated — batch them with
  Story 7's deferred full-stack selenium pass, same as that story did.
