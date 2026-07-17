// The send-and-describe used by every authenticated API client (generations, documents,
// history). Every caller needs the identical "attach the session, map a refusal to something a
// person can read, but never flatten an expired session into a generic failure" behaviour, and a
// second copy is a second place to get the SessionExpiredError carve-out wrong — which is
// exactly what happened while generationApi kept its own: the copy never grew the 409 branch.
//
// LAYERING, and why this file imports a feature while its neighbour `httpClient` refuses to:
// `auth` is not a peer feature here, it is the app's session layer — `documents`, `generations`
// and `history` all sit on top of it, and none of them is imported back. `httpClient` stays
// auth-free for a different and still-live reason (a token-attaching transport would make the
// /auth/refresh client import a client that refreshes — a cycle), so the two layers are:
//   httpClient      — transport, knows nothing
//   send            — transport + session + human-readable refusal
import { isHttpError, type RequestOptions } from './httpClient'
import { authorizedRequest, SessionExpiredError } from '../../features/auth/api/authorizedRequest'

// A stale `version` on PUT — the lost-update guard firing (409 VERSION_CONFLICT). Kept as its
// own type for the same reason as SessionExpiredError: it is not a failure of the save, it is
// the server saying "someone else's write landed first, refetch and retry", which is a protocol
// step rather than something to show the user. Flattening it into a generic Error would leave
// the caller matching on message text to recover.
export class VersionConflictError extends Error {
  constructor() {
    super('Документ был изменён другим сохранением.')
    this.name = 'VersionConflictError'
  }
}

// What the user is told when the server refused. `detail` is FastAPI's shape, `message` is the
// auth endpoints' — accept either, since this app talks to both and neither is going away.
// Measured 2026-07-17: the documents endpoints answer with {"error_code", "message"}, so the
// `message` arm is the live one here.
export function describeFailure(error: unknown, fallback: string): string {
  if (isHttpError(error)) {
    const detail = error.body.detail ?? error.body.message
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    // No usable text: a non-JSON error page, or a body shaped some third way. The status is the
    // only fact left, and it beats a bare "something went wrong" when someone reports this.
    return `${fallback} (HTTP ${error.status})`
  }
  return error instanceof Error && error.message ? error.message : fallback
}

export async function send<T>(path: string, options: RequestOptions, fallback: string): Promise<T> {
  try {
    return await authorizedRequest<T>(path, options)
  } catch (error) {
    // An expired session is NOT an operation failure and must keep its type: the UI shows it as
    // "you are signed out", not as "your document could not be created". Flattening it into a
    // generic Error here would erase the distinction the caller has to make.
    if (error instanceof SessionExpiredError) {
      throw error
    }
    if (isHttpError(error) && error.status === 409) {
      throw new VersionConflictError()
    }
    throw new Error(describeFailure(error, fallback))
  }
}
