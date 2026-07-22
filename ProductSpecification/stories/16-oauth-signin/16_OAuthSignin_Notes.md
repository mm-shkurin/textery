# OAuth sign-in (VK ID + Yandex ID) - Notes & Considerations

## Warnings

### Functional Warnings

- **Single-use handoff code is the whole safety story on the client hop.** A browser
  back/refresh onto `/auth/callback` after success re-POSTs a spent code — the server MUST
  reject it (`INVALID_OR_EXPIRED_OAUTH_CODE`) and the client MUST render an error, never a
  second session. If the client caches the first success and silently re-navigates, a
  shared/logged callback URL becomes a replay foothold.
- **Unknown/missing provider or code.** The callback is reachable by a hand-crafted URL
  (no code, `provider=evil`, `error` and `code` both present). Every shape must resolve to
  the error state deterministically; treat `code`+`error` both present as an error.
- **Auto-create-without-verify trusts the provider's email.** Correct for VK/Yandex (they
  assert it), but it means a provider that returns no email, or an unverified one, must be
  rejected server-side — the frontend cannot see this and must surface whatever error the
  exchange returns rather than assume success.

### UI/UX Warnings

- Provider error / user-cancel must read as "sign-in didn't complete, try again", NOT as a
  wrong-password/validation error and NOT as an indefinite spinner (same distinction Story
  7's 5.6 network-vs-validation work drew).
- The callback screen is a transient interstitial — a slow exchange must show a loading
  state with an eventual failure path (the shared 25s timeout), never a permanent spinner.
- Two providers, one visual language: the buttons should be visually distinct from the
  primary email/password submit so the user understands they're an alternative, not a
  second submit of the form.

### Technical Warnings

- **Token never in a URL.** Only the opaque one-time code appears in `/auth/callback?code=`;
  the real JWTs arrive in the exchange response body and go straight to `authSession`.
  Replace history on success so the spent code doesn't linger in the back stack. This is the
  reason the one-time-code hop was chosen over tokens-in-fragment (Story 7 forbids code/token
  in URL, `07_Authorization_Notes.md`).
- **Redirect-target validation.** `location`/callback params are attacker-reachable; the
  post-sign-in target must go through `safeRedirectTarget` (in-app path only) — an
  open-redirect via a crafted `next`/target param is the classic OAuth-callback bug.
- **Never log the handoff code** (structured logs, error trackers) — it is a live credential
  until exchanged, same logging discipline Story 7 applied to the verification code.
- Provider client secrets / redirect-URI live in `infra/.env` (backend), never the client,
  never committed — Infrastructure guardrails.
- **StrictMode double-fire (frontend, hazard-scan G8).** The callback auto-POSTs the code on
  mount; React 18 StrictMode double-mounts effects, and a re-render or back/refresh can
  re-fire it. Because the code is single-use, the second POST returns the spent-code error —
  which, unguarded, bounces an already-signed-in user back to `/login`. Guard: issue the
  exchange exactly once per code (in-flight lock / dedup) AND ignore a late/duplicate
  rejection once a session is already stored. This is the sharpest frontend correctness bug
  in the flow — pin it with a test asserting exactly one exchange POST per mount.
- **Contract drift (hazard-scan G4).** The frontend builds against a mock; a field-name
  mismatch with the real backend (`expires_at` vs `expiry`) would ship a parse failure no
  mock-defined test catches. Pin the mock to the exact Story-7 login shape, and make the
  parser tolerant of unknown extra fields (additive evolution) — reject only on a MISSING
  usable token, never on an unexpected present one.

---

## Suggestions & Future Enhancements

### Functional Suggestions

- **Account linking / merge** (deferred) — reconcile an OAuth identity with an existing
  email+password account sharing the same email; the natural follow-up before production.
- OAuth on the Register screen and a dedicated method-chooser screen (Login-only this
  iteration).
- Logout (absent app-wide, not OAuth-specific) — a cross-cutting session story.

### UI/UX Suggestions

- Remember last-used provider and surface it first on return visits.

### Technical Suggestions

- Refresh-token rotation for OAuth sessions (plain reuse is the MVP baseline, matching
  Story 7).
- When the backend lands, replace the exchange mock with a contract test pinned to the
  real OpenAPI spec.

---

## Technical Notes

### Load Considerations

Per `ExpectedLoad.txt`: hundreds of concurrent users. The exchange is a single synchronous
POST (no LLM), so no async/queue concern; the handoff-code store must be shared (DB/cache),
never in-process memory, since the backend runs multiple instances — a code minted on one
instance must be redeemable (and then invalidated) on another.

### Security Considerations

- CSRF `state` across the provider handshake is a backend responsibility; the frontend's
  duty is to trust nothing in the callback beyond the opaque code and to validate the
  redirect target.
- One-time + short-TTL handoff code bounds the blast radius of a leaked callback URL to a
  single use within a small window.
- Account enumeration: the exchange error copy must not reveal whether an account already
  existed (auto-create vs. existing) — a generic sign-in-failed / success is enough.
- Deferred linking means an email shared between an email+password account and an OAuth
  sign-in yields two separate accounts for now — a real user expects one identity; flag
  before production, the linking story closes it.

### Infrastructure Notes

- Provider `client_id`/secret, registered `redirect_uri`, and allowed scopes via
  `infra/.env` (backend). No new infra service — reuses the existing Postgres/cache for the
  handoff-code store.

### Integration Notes

- VK ID: `https://id.vk.com/about/business/go/docs` — OAuth 2.1 + PKCE, backend-side.
- Yandex ID: `https://yandex.ru/dev/id/doc/` — Yandex OAuth, backend-side.
- The frontend integrates with NEITHER provider directly — only with the three backend
  `/oauth/*` endpoints defined in `interview.md`. See `interview.md` for the full contract,
  the session-handoff decision, and the scope boundary (linking/unlink/register-buttons
  deferred).

---

## Additional Context

See `interview.md` for the round-by-round decision record: backend-mediated redirect over
client PKCE / SDK widgets, one-time opaque code over tokens-in-fragment / httpOnly cookie,
login-only entry, auto-create-without-verify, and the reuse surface from Story 7
(`authSession`, `apiError`/`loginApi`, `httpClient` timeout, `safeRedirectTarget`,
`LoginForm`/`AuthForm.css`).
