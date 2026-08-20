// The auth session shape on the wire, and the one place that maps it to camelCase.
//
// /auth/login and /auth/oauth/exchange return the SAME body by contract (endpoints.md):
//   200 → {access_token, refresh_token, access_token_expires_at, refresh_token_expires_at}
// Both clients previously carried a verbatim copy of the interface AND the mapping below; they
// differ only in which endpoint they POST to, which is not a reason to fork the boundary. This is
// the sibling of `toAuthApiError`: the clients delegate their error boundary to that seam, and
// their mapping boundary to this one, so a wire-shape change is fixed in exactly one place.
//
// snake_case on the wire → camelCase for the rest of the app. Each field is guarded on its own
// with `String(... ?? '')` so a missing key becomes '' rather than the string "undefined".
export interface SessionTokens {
  accessToken: string
  refreshToken: string
  accessTokenExpiresAt: string
  refreshTokenExpiresAt: string
}

export function sessionTokensFromWire(body: Record<string, unknown>): SessionTokens {
  return {
    accessToken: String(body.access_token ?? ''),
    refreshToken: String(body.refresh_token ?? ''),
    accessTokenExpiresAt: String(body.access_token_expires_at ?? ''),
    refreshTokenExpiresAt: String(body.refresh_token_expires_at ?? ''),
  }
}

// A resolved exchange whose access token is missing, null, or blank is an error, not a sign-in:
// `sessionTokensFromWire` collapses an absent/null token to '', so a token-less 200 lands here as
// ''. `/\S/` mirrors the isUsableMessage / isMalformedCallback convention, so a whitespace-only
// token is unusable too (spec 16_OAuthSignin.md:67 / Notes:55-56).
export function hasUsableAccessToken(session: SessionTokens): boolean {
  return /\S/.test(session.accessToken)
}
