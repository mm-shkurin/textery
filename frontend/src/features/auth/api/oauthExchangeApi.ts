// HTTP client for the OAuth handoff-code exchange (POST /oauth/exchange).
//
// The body shape is IDENTICAL to /auth/login (endpoints.md): snake_case on the wire →
//   200 → {access_token, refresh_token, access_token_expires_at, refresh_token_expires_at}
// so this mirrors loginApi's boundary exactly: it maps snake_case → camelCase and routes any
// rejection through the SAME `toAuthApiError` seam. The rich error/replay/network handling is
// scenario 4.x; here the error path only needs to preserve the {errorCode, message} shape those
// scenarios will match on, so the fallback reports a missing server message AS absence ('').
import { postJson } from '../../../shared/api/httpClient'
import { toAuthApiError } from './apiError'
import { sessionTokensFromWire, type SessionTokens } from './sessionTokens'

export interface OAuthExchangeRequest {
  code: string
}

// The exchange returns the same session shape as /auth/login — see sessionTokens.ts for the
// shared boundary. Kept as a named alias so callers/tests reading `OAuthSession` are unchanged.
export type OAuthSession = SessionTokens

// The exchange owns no display copy of its own — a missing server message is reported as absence
// ('') so the callback (and the 4.x error handling) owns what reaches the screen, mirroring how
// loginApi scopes its fallback rather than forging provenance onto an unrelated code.
function toOAuthExchangeError(error: unknown): unknown {
  return toAuthApiError(error, () => '')
}

export async function oauthExchange(request: OAuthExchangeRequest): Promise<OAuthSession> {
  try {
    const body = await postJson<Record<string, unknown>>('/api/v1/auth/oauth/exchange', {
      code: request.code,
    })
    return sessionTokensFromWire(body)
  } catch (error) {
    throw toOAuthExchangeError(error)
  }
}
