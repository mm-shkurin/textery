# Authorization - API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/auth/register | Create a pending account, issue mocked verification code |
| POST | /api/v1/auth/verify | Confirm the verification code, activate the account |
| POST | /api/v1/auth/resend-code | Issue a new verification code (60s cooldown) |
| POST | /api/v1/auth/login | Authenticate, issue JWT access + refresh token pair |
| POST | /api/v1/auth/refresh | Exchange a valid refresh token for a new access token |

## Notes

- Verification code is returned directly in the `register`/`resend-code` response body
  (mocked — no real email is sent), per `07_Authorization.md`.
- `verify`/`resend-code` take a raw `email`, not an authenticated session — accepted
  trade-off documented in `07_Authorization_Notes.md` (Security Considerations).
- Errors use a uniform `{ "error_code": string, "message": string }` shape; `message`
  is always a generic, client-safe string — never a raw stack trace or internal detail
  (hazard-scan group 7 guard). See [`../../api-specs/README.md`](../../api-specs/README.md)
  for the shared handler and app-wide implications.
