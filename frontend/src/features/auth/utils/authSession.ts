// Where the auth tokens live.
//
// The backend returns tokens in the RESPONSE BODY, not an httpOnly cookie, so the client is
// obliged to store them and no XSS-proof option exists here — only a choice of blast radius.
// Decided with the user 2026-07-16: sessionStorage.
//   - vs localStorage: a stolen token dies with the tab instead of outliving the browser.
//   - vs memory + /refresh on reload: strictly safer for the access token, but it is refresh
//     logic and a race, and we are moving fast; sessionStorage survives F5 with far less code,
//     which means far fewer places to get it wrong.
// The real fix is httpOnly + SameSite cookies set by the backend. Until then this is a
// documented accepted risk, not an oversight. React escapes by default and the app has no
// `dangerouslySetInnerHTML` (verified), so the XSS surface is small — but it is not zero.
//
// Never log these values, never put them in a URL or query string: 07_Authorization_Notes.md
// requires treating auth material as a real credential regardless of the mocked email flow.
const ACCESS_TOKEN_KEY = 'textery.auth.accessToken'
const REFRESH_TOKEN_KEY = 'textery.auth.refreshToken'

export interface AuthSession {
  accessToken: string
  refreshToken: string
}

// sessionStorage throws in a few real environments (Safari private mode historically, and any
// embedding that disables storage). Auth must not hard-crash the app because storage is
// unavailable, so reads and writes degrade instead of throwing.
function safeSet(key: string, value: string): boolean {
  try {
    window.sessionStorage.setItem(key, value)
    return true
  } catch {
    return false
  }
}

function safeGet(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key)
  } catch {
    return null
  }
}

export function saveSession(session: AuthSession): boolean {
  const storedAccess = safeSet(ACCESS_TOKEN_KEY, session.accessToken)
  const storedRefresh = safeSet(REFRESH_TOKEN_KEY, session.refreshToken)
  return storedAccess && storedRefresh
}

export function getAccessToken(): string | null {
  return safeGet(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return safeGet(REFRESH_TOKEN_KEY)
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken())
}

export function clearSession(): void {
  try {
    window.sessionStorage.removeItem(ACCESS_TOKEN_KEY)
    window.sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  } catch {
    // Nothing to clear if storage is unavailable.
  }
}
