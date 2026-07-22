# Story 16: OAuth sign-in (VK ID + Yandex ID) — Progress

Follow-up to Story 7, which deferred VK ID / Yandex ID OAuth. Frontend-first: the backend
OAuth slice is WIP, so this story's spec DEFINES the backend contract (see `interview.md`,
`endpoints.md`, `api-specs/oauth_*.yaml`) and the frontend is built against a mock of
`POST /oauth/exchange`.

Split layout: this shared `progress.md` (Spec + narrative), `progress-frontend.md`
(Frontend Scenarios), and `progress-backend.md` (API/Integration/Security/Infra — bootstrapped
by the backend session when it starts). Load = n/a (login-class one-shot).

## Spec
- [x] interview
- [x] story
- [x] mockups
- [x] api-spec
- [x] test-spec

## Decisions (carried into scenarios)

- **Backend-mediated redirect**, not client PKCE / SDK widgets — no provider secret or
  third-party script on the client.
- **One-time opaque handoff code** for the session hop — token never rides a URL; the
  frontend exchanges the code at `POST /oauth/exchange` for the Story-7 login session shape
  and stores it via the existing `authSession`.
- **Login-only** entry; **auto-create on first sign-in, skip verify**.
- **Account-linking DEFERRED** — an OAuth email matching an existing email+password account
  creates a SEPARATE account for now (also the takeover guard, pinned in `01_API_Tests.md`
  3.8 / `05_Security_Tests.md`).
- Selenium legs are backend-gated → deferred `[S]`, batched for a full-stack selenium pass
  once the backend endpoints land (same pattern Story 7 used). `demo` skipped visual-only.
