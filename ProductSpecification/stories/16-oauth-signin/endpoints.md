# OAuth sign-in (VK ID + Yandex ID) - API Endpoints

Backend contract for the WIP OAuth slice. `provider` ∈ `vk | yandex`. Backend-mediated:
the client holds no provider secret and never calls a provider directly — only these three
endpoints under `/api/v1/auth/oauth`.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/auth/oauth/{provider}/start | Full-page nav target of the button; 302-redirects to the provider auth page (client_id + CSRF state server-side). _Planned, backend WIP._ |
| GET | /api/v1/auth/oauth/{provider}/callback | Provider's redirect target (backend-only). Validates state, exchanges the provider code, resolves/auto-creates the account, mints a one-time handoff code, 302-redirects to the frontend `/auth/callback`. _Planned, backend WIP._ |
| POST | /api/v1/auth/oauth/exchange | Frontend exchanges the one-time handoff code for a JWT session (Story 7 login shape). _Planned, backend WIP._ |

## Notes

- **Session body is identical to `/auth/login`** (`access_token`, `refresh_token`,
  `access_token_expires_at`, `refresh_token_expires_at`) — the frontend maps it through the
  same boundary into `authSession`. See [`../../api-specs/auth_login.yaml`](../../api-specs/auth_login.yaml).
- **The token never rides in a URL.** Only the opaque one-time handoff code appears in the
  callback redirect (`/auth/callback?code=…`); the real JWTs come back in the `exchange`
  response body. Code is single-use + short-TTL (hazard-scan G2/G3: atomic redeem, exactly
  one 200 under concurrent exchange).
- **Auto-create without verify.** First sign-in creates the account from provider-asserted,
  NFC-normalized + case-folded email (hazard-scan G1 key normalization); identity unique per
  `(provider, subject)` (G3). No `is_verified` step — the provider asserts the email.
- Errors use the app-wide `{ "error_code": string, "message": string }` shape; `message` is
  a generic client-safe string. See [`../../api-specs/README.md`](../../api-specs/README.md).
- `start`/`callback`/`exchange` are rate-limited (hazard-scan G6). Provider `client_id`/
  secret/redirect_uri/scopes come from `infra/.env` and fail-fast at boot if unset (G7).
