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
// The requested document does not exist for this session — absent, or owned by another account
// (endpoints.md: both answer with the same 404 body, never 403, so the client cannot and must not
// tell them apart). Its own type for the same reason as VersionConflictError: the caller routes it
// to "этого документа нет" rather than to the generic failure screen, and matching on message text
// to recover that is what having a type avoids.
export class DocumentNotFoundError extends Error {
  constructor() {
    super('Документ не найден')
    this.name = 'DocumentNotFoundError'
  }
}

// OPT-IN, per call — and deliberately NOT the unconditional branch the 409 mapping is.
// `error_code: 'NOT_FOUND'` is shared by ALL seven endpoints, so a global branch would also fire
// for generation polling, both history lists and PUT /documents/{id} — callers that never narrow
// the new type. `useDocumentSave` would fall through to "Повторите — текст пока только в
// редакторе" (retry advice that can never succeed), and useGeneration/useHistoryList render
// `error.message` verbatim, so a missing GENERATION would read "Документ не найден". Only a
// caller that knows the 404 is about a document, and handles it, asks for the mapping.
export interface RefusalMapping {
  notFound?: boolean
}

// "The server refused, and it named this reason." Both mapped refusals below key on the CODE and
// not the bare status, so the pairing is the concept — naming it keeps each branch one line of
// intent instead of three conjuncts the reader has to re-derive.
function refusedWith(error: unknown, status: number, code: string): boolean {
  return isHttpError(error) && error.status === status && error.body.error_code === code
}

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

export async function send<T>(
  path: string,
  options: RequestOptions,
  fallback: string,
  refusals: RefusalMapping = {},
): Promise<T> {
  try {
    return await authorizedRequest<T>(path, options)
  } catch (error) {
    // An expired session is NOT an operation failure and must keep its type: the UI shows it as
    // "you are signed out", not as "your document could not be created". Flattening it into a
    // generic Error here would erase the distinction the caller has to make.
    if (error instanceof SessionExpiredError) {
      throw error
    }
    // The CODE, not the bare status. 409 means "conflict", which is not one thing: PUT
    // /documents/{id} sends VERSION_CONFLICT for a stale version, but POST /documents carries an
    // Idempotency-Key and can 409 over the key itself — an operation that has no version at all.
    // Matching on the status alone told a user whose create collided "Документ был изменён
    // другим сохранением": a lost-update message for a document that was never saved once, and
    // one that sends them to reopen a document that does not exist. Any other 409 keeps the
    // caller's fallback text, which at least names the operation that actually failed.
    if (refusedWith(error, 409, 'VERSION_CONFLICT')) {
      throw new VersionConflictError()
    }
    // The CODE again, not the bare status — and the trade is explicit: a 404 that carries NO
    // `error_code` (a proxy's HTML 404, an empty body — `performRequest` substitutes `{}`) stays a
    // generic described Error. That is the safer half of the miss: the endpoint's own 404 always
    // carries the code, so what falls through here is a request that never reached the API, and
    // telling that user "документа не существует" would send them to delete work that is fine.
    if (refusals.notFound && refusedWith(error, 404, 'NOT_FOUND')) {
      throw new DocumentNotFoundError()
    }
    throw new Error(describeFailure(error, fallback))
  }
}
