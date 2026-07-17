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

// sessionStorage fires no event for writes made by its own tab, and the session is per-tab by
// construction — so nothing tells React that a token appeared or vanished. Without this,
// `isAuthenticated()` read during render is a value that only changes when something ELSE
// happens to re-render, which is how a signed-out user keeps looking signed in until they
// click something. Every mutation below notifies; `useAuthSession` subscribes.
type SessionListener = () => void

const listeners = new Set<SessionListener>()

export function subscribeAuthSession(listener: SessionListener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function notifySessionChanged(): void {
  for (const listener of [...listeners]) {
    listener()
  }
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
  notifySessionChanged()
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
  notifySessionChanged()
}

// Signing out, as far as this client can.
//
// There is NO `POST /auth/logout` on the backend (verified 2026-07-17 against the running
// instance's OpenAPI document: register/verify/login/refresh, and nothing else). So this drops
// the tokens from this tab and no more.
//
// And an endpoint alone would not be enough: the tokens are stateless JWTs and the backend
// keeps no token store — a spent refresh token still returns 200 on replay (probed the same
// day). Nothing server-side can invalidate an issued token before its own expiry, so a copy
// exfiltrated before the click keeps working for up to 7 days. Closing that needs a revocation
// list on the backend, not just a route. Real, accepted, and worth stating plainly: this is not
// "the session is destroyed", it is "this tab forgets the session".
//
// Sign-out is separated from `clearSession` by INTENT, not mechanics. `clearSession` is the
// involuntary path (refresh failed, storage broke); this is the user asking. They are the same
// two lines today and will not stay that way — the revocation call belongs here and nowhere
// near the expiry handler, which cannot afford to await a network round-trip.
export function logout(): void {
  clearSession()
}
