# OAuth sign-in (VK ID + Yandex ID)

## Brief Description

From the Login screen a user signs in with VK ID or Yandex ID. The backend runs the whole
provider handshake and hands the frontend a one-time opaque code, which the frontend
exchanges for the same JWT session Story 7 issues. First sign-in auto-creates the account.

## Flow

1. On `/login` the user clicks "Войти через VK ID" or "Войти через Yandex ID".
2. The browser does a full-page navigation to `GET /api/v1/auth/oauth/{provider}/start`.
3. The backend 302-redirects to the provider's auth page (client secrets + CSRF `state`
   held server-side).
4. The user authorizes; the provider redirects to the backend callback with a provider code.
5. The backend validates `state`, exchanges the provider code, resolves or auto-creates the
   account (provider-verified email → no verify step), and mints a single-use, short-TTL
   opaque handoff code.
6. The backend 302-redirects the browser to the frontend: `/auth/callback?code=OPAQUE&
   provider={provider}` on success, or `/auth/callback?error=CODE` on failure.
7. The `/auth/callback` screen shows a loading state and POSTs `{ code }` to
   `POST /api/v1/auth/oauth/exchange`.
8. On 200 the frontend stores the returned JWT session (reusing Story 7 `authSession`) and
   navigates to the app shell with history replaced.
9. On an `error=` param, an exchange failure, or a replayed/expired code, the user is
   returned to `/login` with a clear, non-technical message.

## Acceptance Criteria

- Each provider button navigates the full page to that provider's `start` URL (no fetch).
- A successful callback exchanges the opaque code exactly once and lands the user in the
  app shell with a valid access + refresh token stored.
- The access/refresh token never appears in any URL, browser history, or log — only the
  opaque handoff code does, and only until it is exchanged.
- A second visit to `/auth/callback` with an already-used or expired code shows an error
  and does NOT create a second session (single-use enforced server-side; client shows the
  error, never a silent re-login).
- Provider error / user-cancel (`error=` param) returns to login with a distinct message,
  not a validation-style or an indefinite-spinner state.
- An unknown `provider` value, a missing `code`, or a malformed callback URL resolves to
  the error state, never a crash or a blank screen.
- An exchange network/timeout/5xx is retry-affording (back to login), reusing the shared
  25s httpClient timeout and login's network-error treatment.
- The post-sign-in redirect target is validated (`safeRedirectTarget`, in-app path only) —
  a crafted callback param can never drive an open redirect.
- The email+password login/register flows are unchanged (no regression), and an OAuth
  sign-in produces a session object identical in shape to an email+password login.
- The callback issues the exchange POST **exactly once per code** even if the effect
  mounts twice (React StrictMode / re-render); a duplicate or late exchange rejection
  arriving **after** a session was already stored is ignored, not a bounce back to login.
- The exchange-response parser **ignores unknown/extra fields** (additive backend
  evolution) rather than rejecting an otherwise-valid session.
- Sign-in-failure copy is **identical whether the account was auto-created or already
  existed** (no account enumeration).
- An oversized or empty callback `code` resolves to the error state **before** any exchange
  POST is sent; an unrecognized `error=` code falls back to generic sign-in-failed copy,
  never blank or raw.

## Validation Rules

| Field | Rule |
|-------|------|
| provider (route/param) | must be exactly `vk` or `yandex`; any other value → error state, not a request |
| callback `code` | opaque string, required for the success path; bounded max length — over-length or empty (`?code=`) → error state, NOT POSTed to exchange; single-use (server-enforced), short-TTL; never logged, never persisted in history after exchange |
| callback `error` | when present, routes to the login error state; its value is mapped to copy, never rendered raw |
| redirect target | in-app absolute path only, via `safeRedirectTarget`; anything else falls back to the app-shell default |
| exchange response | `{ access_token, refresh_token, access_token_expires_at, refresh_token_expires_at }` (Story 7 login shape); a 200 missing a usable token is an error, not a sign-in |

## Screen States

- Login form with two OAuth buttons added below the email/password form.
- OAuth callback screen — loading (exchange in flight).
- OAuth callback error → redirect to login with a provider-sign-in error message.
- Authenticated app shell (session stored, protected routes reachable).

## Core Requirements

- New `/auth/callback` route in the plain `<BrowserRouter>` (App.tsx); no data-router
  migration (Story 7 constraint).
- New `oauthExchangeApi` mapping the exchange response through the existing `apiError` /
  login-session boundary (camelCase) into `authSession` (sessionStorage) — no new token model.
- Provider→label/start-path config (`vk`, `yandex`) as data, not branching, so an unknown
  provider is a rejected value rather than an unhandled case.
- OAuth buttons are full-page navigations, NOT fetch — no provider `client_id`/secret or
  third-party script on the client (backend-mediated).
- Callback error/replay/network states are form-owned copy (reuse `authMessages`), distinct
  from validation errors — the exchange POST rides the shared 25s timeout.
- Backend contract (WIP, defined in `interview.md`): the three endpoints, provider secrets
  in `infra/.env`, single-use + short-TTL handoff-code store, and auto-create-without-verify
  account resolution. Frontend builds against a mock of `POST /oauth/exchange`, pinned to
  the exact Story-7 login field contract so the mock can't define a shape the real backend
  won't deliver.

### Backend contract obligations (folded from hazard-scan)

Named here at contract altitude; the forcing tests land in the backend/integration/security
scenarios, but a downstream test must be able to go red on each:

- **Atomic single-use redeem.** The handoff code is redeemed by a single atomic
  compare-and-delete / conditional update — correct under two exchanges of the same code
  arriving simultaneously on different instances: exactly one 200 + one rejection, never two
  sessions. (Covers both sequential replay and the concurrent race in one guard.)
- **Redeem-and-issue atomicity.** A code that yields no session rolls back its redemption
  (never silently burned); account auto-create + code lifecycle commit all-or-nothing.
- **Identity uniqueness.** An OAuth identity is unique per `(provider, subject)` —
  concurrent first sign-ins for one identity yield exactly one account, the second resolves
  to it (not a duplicate).
- **Email keyed after normalization.** The provider email is UTF-8, NFC-normalized and
  case-folded (invariant locale) before use as the account-resolution key — the same human
  resolves to one account across case / normalization variance.
- **Read-your-write across instances.** A freshly-minted code is redeemable on any instance
  before the redirect completes (strongly-consistent read on the shared store) — the first
  legitimate exchange never spuriously fails.
- **Injectable clock.** TTL/expiry is evaluated against an injectable clock (expired-now
  rejected, expires-now accepted) so the boundary is testable.
- **Fail-fast config.** OAuth env config (`redirect_uri`, scopes, client secret) fails loud
  at startup if unset/blank — never a lazy dev-fallback surfacing at first prod sign-in.
- **No over-binding on auto-create.** Auto-create binds only provider-asserted claims; the
  exchange request body is `{ code }` only, so no client field can over-bind onto the new
  account.
- **Abuse bound.** Repeated `start` / `callback` / `exchange` hits are rate-limited
  (per-IP / per-session).
- **Lost-response recovery.** If the exchange response is lost after the server committed
  (network drop / timeout), the user restarts from login for a fresh code — a spent-code
  error is a recoverable path, not a dead-end.

Accepted trade-off (see Notes): account-linking is deferred — an OAuth sign-in whose email
matches an existing email+password account creates a SEPARATE account for now. Documented;
closed by the future linking story before any production rollout.
