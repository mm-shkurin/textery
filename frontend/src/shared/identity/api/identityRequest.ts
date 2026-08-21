// A read that must NEVER end the session, no matter how it fails.
//
// `authorizedRequest` answers a 401 by renewing, and `performRenewal` calls `clearSession()` on
// ANY renewal failure — a 500, a timeout, the network being down. That is correct for a request
// the USER made: the session really is unusable and saying so once beats failing silently
// forever. It is catastrophic for `GET /me`, which after story 13 fires on every authenticated
// page at load, unprompted. One blip during a rolling deploy would otherwise sign out every open
// tab at once and take the unsaved text in the editor with it.
//
// So this is a deliberate second path, not a duplicate of the first. It attaches the token, and
// on a 401 it renews ONCE by calling the refresh client directly — bypassing `performRenewal`,
// whose whole job is the `clearSession()` this path must not reach. Everything else (5xx, a
// timeout, a refresh that itself fails) surfaces as a plain rejection: the caller degrades its
// identity display and the stored session is left exactly as it was. Only a user-initiated
// request may conclude a session is dead.
//
// It duplicates renewal rather than sharing `authorizedRequest`'s single-flight, which means a
// /me renewal can race a user-action renewal. That is safe against this backend: refresh tokens
// are stateless JWTs and are not revoked on use — replaying one returns another 200 (verified
// 2026-07-17, see refreshApi.ts). If the backend ever gains real rotation, this must join the
// shared single-flight — WITHOUT inheriting its clearSession.
import { isHttpError, request, type RequestOptions } from '../../api/httpClient'
import { getAccessToken, getRefreshToken, saveSession } from '../../session/authSession'
import { refresh } from '../../session/refreshApi'

function withBearer(options: RequestOptions, token: string): RequestOptions {
  return { ...options, headers: { ...options.headers, Authorization: `Bearer ${token}` } }
}

// The profile is unavailable. It says nothing about whether the session is alive — deliberately,
// because the header must not draw a conclusion this error does not carry.
export class IdentityUnavailableError extends Error {
  constructor() {
    super('Данные учётной записи сейчас недоступны.')
    this.name = 'IdentityUnavailableError'
  }
}

async function renewWithoutEndingSession(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null
  try {
    const renewed = await refresh(refreshToken)
    if (!renewed.accessToken) return null
    saveSession(renewed)
    return renewed.accessToken
  } catch {
    // Swallowed on purpose, and this `catch` is the point of the whole module: the equivalent
    // line in `performRenewal` is `clearSession()`.
    return null
  }
}

export async function identityRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getAccessToken()
  if (!token) throw new IdentityUnavailableError()

  try {
    return await request<T>(path, withBearer(options, token))
  } catch (error) {
    if (!(isHttpError(error) && error.status === 401)) {
      throw new IdentityUnavailableError()
    }
    // Another request may have renewed while this one was in flight; replay with what is current
    // before spending a refresh call to re-derive it.
    const current = getAccessToken()
    const renewedToken = current && current !== token ? current : await renewWithoutEndingSession()
    if (renewedToken === null) throw new IdentityUnavailableError()
    try {
      return await request<T>(path, withBearer(options, renewedToken))
    } catch {
      // Exactly one retry. A 401 on a brand-new token is not staleness and will not become it.
      throw new IdentityUnavailableError()
    }
  }
}
