// STUB (red-frontend 3.1). The exchange client does not exist yet — green-frontend implements the
// real POST /api/v1/auth/oauth/exchange boundary, mapping the snake_case session body onto
// camelCase through the SAME apiError seam as loginApi (see endpoints.md: body identical to
// /auth/login). This throwing stub exists only so the (skipped) 3.1 test can resolve its import;
// it holds NO behavior.
export interface OAuthExchangeRequest {
  code: string
}

export interface OAuthSession {
  accessToken: string
  refreshToken: string
  accessTokenExpiresAt: string
  refreshTokenExpiresAt: string
}

export function oauthExchange(_request: OAuthExchangeRequest): Promise<OAuthSession> {
  throw new Error('oauthExchange not implemented (red-frontend 3.1)')
}
