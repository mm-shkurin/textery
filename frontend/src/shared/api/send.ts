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
import { RequestTimeoutError, isHttpError, type RequestOptions } from './httpClient'
import { authorizedRequest, SessionExpiredError } from '../session/authorizedRequest'

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
    // The origin's catch-all 500 handler answers with a fixed ENGLISH sentence ("An unexpected
    // error occurred. Please try again.") and the code INTERNAL_ERROR — rendering it verbatim puts
    // English on a Russian screen at every call site at once. That body carries no reason, so
    // nothing is lost by preferring the caller's fallback, which at least names the operation.
    // Keyed on the code AND the status class, deliberately narrowly: a 5xx that EXPLAINS itself
    // (a provider quota, a rejected size) keeps its text, because the message is the only place
    // that explanation exists; a 4xx is a decided answer already addressed to the user; and a
    // codeless 500 is not this handler's shape at all.
    const isOriginCatchAll = error.status >= 500 && error.body.error_code === 'INTERNAL_ERROR'
    if (!isOriginCatchAll && typeof detail === 'string' && detail.trim()) {
      return detail
    }
    // No usable text: a non-JSON error page, or a body shaped some third way. The status is the
    // only fact left, and it beats a bare "something went wrong" when someone reports this.
    return `${fallback} (HTTP ${error.status})`
  }
  return error instanceof Error && error.message ? error.message : fallback
}

/**
 * The failure to rethrow UNCHANGED, or `null` when it should be flattened to text.
 *
 * Three kinds of failure carry information past this boundary, and each one was
 * flattened here at some point with a real consequence:
 *
 * 1. **An expired session is not an operation failure.** The UI shows it as "you
 *    are signed out", not "your document could not be created". Flattening erases
 *    the distinction the caller has to make.
 *
 * 2. **A version conflict is matched on the CODE, not the bare status.** 409 is not
 *    one thing: `PUT /documents/{id}` sends `VERSION_CONFLICT` for a stale version,
 *    while `POST /documents` carries an Idempotency-Key and can 409 over the key
 *    itself — an operation with no version at all. Matching on the status alone told
 *    a user whose create collided «Документ был изменён другим сохранением»: a
 *    lost-update message for a document that was never saved once, sending them to
 *    reopen a document that does not exist. Any other 409 keeps the caller's
 *    fallback, which at least names the operation that failed.
 *
 * 3. **A failure whose OUTCOME IS UNKNOWN keeps its shape.** A client-side deadline
 *    and any 5xx are the two answers that do not say whether the server took the
 *    write. The autosave retry policy decides "retry?" and "may this have landed?"
 *    from `error.status` and the timeout's identity (`autosaveRetryPolicy.ts`), and
 *    `new Error(describeFailure(...))` destroys both: a status becomes a substring
 *    of a sentence, and a `RequestTimeoutError` becomes an `Error` whose message
 *    merely reads 'Request timed out'. Flattening here is what made the whole
 *    H9.3/H9.4 retry branch unreachable in production while every fixture that
 *    hand-rolled `{status: 5xx}` stayed green.
 *
 * 4xx keeps flattening: those are decided answers, and no caller has to classify
 * them. Callers that only RENDER a preserved failure must not read `.message` off
 * it — `HttpError` is a bare object literal, not an `Error` — they call
 * `describeFailure`, which handles both shapes.
 */
function preserved(error: unknown): unknown | null {
  if (error instanceof SessionExpiredError) return error
  if (isHttpError(error) && error.status === 409 && error.body.error_code === 'VERSION_CONFLICT') {
    return new VersionConflictError()
  }
  if (error instanceof RequestTimeoutError || (isHttpError(error) && error.status >= 500)) {
    return error
  }
  return null
}

export async function send<T>(path: string, options: RequestOptions, fallback: string): Promise<T> {
  try {
    return await authorizedRequest<T>(path, options)
  } catch (error) {
    const keep = preserved(error)
    if (keep !== null) throw keep
    throw new Error(describeFailure(error, fallback))
  }
}
