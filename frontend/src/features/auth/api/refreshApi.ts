// HTTP client for the token-refresh endpoint.
//
// Contract probed against the running backend on 2026-07-17 (not read off the spec):
//   POST /api/v1/auth/refresh  {refresh_token}
//   200 → {access_token, refresh_token, access_token_expires_at, refresh_token_expires_at}
//   401 → {error_code: "INVALID_REFRESH_TOKEN", message: "The refresh token is invalid or has
//          expired."}
//   Access tokens carry a 15-minute expiry; refresh tokens, 7 days.
//
// The 200 carries a NEW refresh token, but the one just spent is NOT revoked — replaying it
// returns another 200 (verified). These are stateless JWTs and the backend keeps no token
// store, so nothing can invalidate one before its own expiry. Do not write code that assumes
// otherwise.
//
// Persist BOTH halves anyway. Each refresh issues a refresh token expiring 7 days from NOW, so
// storing it slides the window and an active user stays signed in. Keeping the original instead
// caps every session at 7 days from first login and then ends it mid-use, with no failure
// anywhere to explain why.
//
// This calls `postJson` directly rather than `authorizedRequest`: the refresh token travels in
// the body, no Authorization header is involved, and routing it through the retry layer would
// have a failed refresh trigger a refresh.
import { postJson } from '../../../shared/api/httpClient'
import type { AuthSession } from '../utils/authSession'

export async function refresh(refreshToken: string): Promise<AuthSession> {
  const body = await postJson<Record<string, unknown>>('/api/v1/auth/refresh', {
    refresh_token: refreshToken,
  })
  // The wire is snake_case; the rest of the app sees camelCase, and this is the boundary.
  // Rejections pass through untouched — the only caller (`authorizedRequest`) treats every
  // failure the same way, so translating them here would add a vocabulary nobody reads.
  return {
    accessToken: String(body.access_token ?? ''),
    refreshToken: String(body.refresh_token ?? ''),
  }
}
