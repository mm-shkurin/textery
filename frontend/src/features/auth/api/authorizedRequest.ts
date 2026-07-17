// The one way to call an endpoint that needs a session: attach the access token, and when the
// backend says 401, renew once and replay the request rather than surfacing a failure the user
// did nothing to cause.
//
// Access tokens live ~15 minutes. Without this layer every session turns into silent refusals
// at the quarter-hour mark while a perfectly good refresh token sits unused in storage.
import { isHttpError, request, type RequestOptions } from '../../../shared/api/httpClient'
import { clearSession, getAccessToken, getRefreshToken, saveSession } from '../utils/authSession'
import { refresh } from './refreshApi'

// The session is gone and could not be renewed — distinct from "the server rejected what you
// asked for". Callers must not render this as a failure of the operation: nothing is wrong with
// the request, the user is simply signed out, and the UI's job is to say so once rather than to
// blame the button they pressed.
export class SessionExpiredError extends Error {
  constructor() {
    super('Сессия истекла. Войдите снова.')
    this.name = 'SessionExpiredError'
  }
}

function withBearer(options: RequestOptions, token: string): RequestOptions {
  return { ...options, headers: { ...options.headers, Authorization: `Bearer ${token}` } }
}

function isUnauthorized(error: unknown): boolean {
  return isHttpError(error) && error.status === 401
}

// Renewal is SHARED, not per-request. The generation screen polls, so an expiry lands on
// several in-flight requests at once; without this they each fire their own refresh, and the
// last one to finish decides which token is stored while the others' tokens are overwritten
// mid-use. One refresh per expiry keeps the stored session single-valued and keeps a burst of
// N pollers from becoming a burst of N auth calls.
//
// This is NOT protection against a rotation race: the backend does not revoke a spent refresh
// token (verified 2026-07-17 — replaying one returns another 200), so a duplicate refresh would
// succeed rather than sign anyone out. If the backend ever gains real rotation, this
// single-flight becomes load-bearing for correctness too — but today it earns its place on
// coherence and request count alone.
let inFlightRenewal: Promise<boolean> | null = null

function renewSession(): Promise<boolean> {
  if (!inFlightRenewal) {
    // Cleared in `finally`, so a later 401 can renew again. Assigning before the `finally`
    // attaches would leave a settled promise cached forever.
    inFlightRenewal = performRenewal().finally(() => {
      inFlightRenewal = null
    })
  }
  return inFlightRenewal
}

async function performRenewal(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    clearSession()
    return false
  }
  try {
    const renewed = await refresh(refreshToken)
    // Persisting is part of succeeding, not a side effect of it. A token we cannot store is a
    // token the next request cannot send, so it would 401, refresh, fail to store, and 401
    // again — an unbounded auth call per request, invisible except as load. Report the storage
    // failure as the sign-out it effectively is.
    if (!renewed.accessToken || !saveSession(renewed)) {
      clearSession()
      return false
    }
    return true
  } catch {
    // Any failure — 401 on an expired refresh token, a 500, the network being down — ends the
    // session. Keeping tokens we could not renew only defers the same dead end to the next
    // request, and by then the user has typed something they are about to lose.
    clearSession()
    return false
  }
}

export async function authorizedRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getAccessToken()
  // No token, no request. This endpoint needs a session; sending anonymously would ask the
  // backend a question we already know the answer to — and today's backend answers it WRONG.
  // Probed 2026-07-17 against the running instance: `POST /api/v1/generations` returns 201 to
  // an anonymous caller AND 201 to one holding the literal token "garbage". It declares no
  // security scheme and does not read the header at all.
  //
  // So this guard is the client declining to walk through a hole it can see. It is NOT a fix
  // for that hole — anyone with curl skips this code entirely, as the probe just did. The fix
  // is the backend rejecting a request with no valid token, and it is still owed.
  if (!token) {
    throw new SessionExpiredError()
  }

  try {
    return await request<T>(path, withBearer(options, token))
  } catch (error) {
    if (!isUnauthorized(error)) {
      throw error
    }

    // A concurrent request may have already renewed while this one was in flight, so this 401
    // answers a token that is already superseded. Refreshing again would be an auth call to
    // re-derive what is sitting in storage. Replay with whatever is current instead.
    const current = getAccessToken()
    if (current && current !== token) {
      return await request<T>(path, withBearer(options, current))
    }

    if (!(await renewSession())) {
      throw new SessionExpiredError()
    }
    const renewedToken = getAccessToken()
    if (!renewedToken) {
      throw new SessionExpiredError()
    }
    // Replayed with the ORIGINAL `options` on purpose: a POST carrying an `Idempotency-Key`
    // must repeat the same key, or the backend treats the replay as a second, distinct request
    // and the user gets two generations for one click.
    //
    // Exactly one retry. A 401 on the replay means the brand-new token was refused, which is
    // not a staleness problem and will not become one — looping on it is how a client
    // hammers an endpoint until the account is locked.
    return await request<T>(path, withBearer(options, renewedToken))
  }
}
